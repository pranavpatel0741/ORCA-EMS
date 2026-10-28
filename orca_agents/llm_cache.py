"""LLM calls with record / replay caching (PLAN §14.8).

Cache key = hash(agent id, model, prompt version, serialized input). Modes (`LLM_MODE`):
- `live`: use the cache when it has the answer, otherwise call the API and store it
- `record`: always call the API and store (overwrite) the answer
- `cache_only`: never call the API; a cache miss raises `CacheMiss`

A backend turns (agent spec, input payload) into a typed output. `OpenAIAgentsBackend` uses the
OpenAI Agents SDK; tests use a scripted backend and never touch the network.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

import config.settings as settings

CACHE_DIR = settings.DATA_DIR / "llm_cache"
PROMPT_DIR = Path(__file__).parent / "prompts"


class CacheMiss(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str  # e.g. "dispatch", "hospital:A"
    prompt_file: str  # file name in prompts/
    output_type: type[BaseModel]
    prompt_vars: tuple[tuple[str, str], ...] = ()
    tools: tuple[Any, ...] = ()

    @property
    def instructions(self) -> str:
        text = (PROMPT_DIR / self.prompt_file).read_text()
        body = text.split("\n", 2)[2] if text.startswith("Version:") else text
        return body.format(**dict(self.prompt_vars)) if self.prompt_vars else body

    @property
    def version(self) -> str:
        first = (PROMPT_DIR / self.prompt_file).read_text().splitlines()[0]
        return first.split(":", 1)[1].strip() if first.startswith("Version:") else "0"


@dataclass
class CallRecord:
    agent: str
    model: str
    key: str
    cache_hit: bool
    tokens: int = 0
    latency_ms: float = 0.0  # wall clock; excluded from reproducibility comparisons

    def as_event(self) -> dict[str, Any]:
        return {"agent": self.agent, "model": self.model, "key": self.key,
                "cache_hit": self.cache_hit, "tokens": self.tokens,
                "latency_ms": round(self.latency_ms, 1)}


class Backend(Protocol):
    model: str

    def run(self, spec: AgentSpec, payload: dict[str, Any], context: Any) -> tuple[BaseModel, int]:
        """Return (typed output, tokens used)."""


class OpenAIAgentsBackend:
    """Runs an SDK `Agent` with structured output and read-only tools."""

    def __init__(self, model: str | None = None, max_turns: int = 6,
                 timeout_s: float = 60.0) -> None:
        self.model = model or settings.OPENAI_MODEL
        if not self.model:
            raise RuntimeError("OPENAI_MODEL is not set (see .env.example)")
        self.max_turns = max_turns
        self.timeout_s = timeout_s

    def run(self, spec: AgentSpec, payload: dict[str, Any], context: Any) -> tuple[BaseModel, int]:
        from agents import Agent, Runner

        agent = Agent(name=spec.agent_id, instructions=spec.instructions, model=self.model,
                      output_type=spec.output_type, tools=list(spec.tools))
        prompt = json.dumps(payload, sort_keys=True, default=str)

        async def go():
            return await asyncio.wait_for(
                Runner.run(agent, prompt, context=context, max_turns=self.max_turns),
                timeout=self.timeout_s)

        result = asyncio.run(go())
        usage = result.context_wrapper.usage
        return result.final_output_as(spec.output_type), int(usage.total_tokens or 0)


@dataclass
class LLMClient:
    backend: Backend | None
    mode: str = field(default_factory=lambda: settings.LLM_MODE)
    cache_dir: Path = CACHE_DIR
    model_name: str | None = None  # for cache_only replay without a backend

    @property
    def model(self) -> str:
        if self.backend:
            return self.backend.model
        return self.model_name or settings.OPENAI_MODEL or "unset"

    def key(self, spec: AgentSpec, payload: dict[str, Any]) -> str:
        blob = json.dumps({"agent": spec.agent_id, "model": self.model, "prompt": spec.version,
                           "input": payload}, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:24]

    def _path(self, spec: AgentSpec, key: str) -> Path:
        return self.cache_dir / spec.agent_id.replace(":", "_") / f"{key}.json"

    def call(self, spec: AgentSpec, payload: dict[str, Any],
             context: Any = None) -> tuple[BaseModel, CallRecord]:
        key = self.key(spec, payload)
        path = self._path(spec, key)
        if self.mode in ("live", "cache_only") and path.exists():
            stored = json.loads(path.read_text())
            out = spec.output_type.model_validate(stored["output"])
            return out, CallRecord(spec.agent_id, self.model, key, True, stored.get("tokens", 0))
        if self.mode == "cache_only" or self.backend is None:
            raise CacheMiss(f"{spec.agent_id}: no cached response for key {key}")
        started = time.perf_counter()
        out, tokens = self.backend.run(spec, payload, context)
        latency = (time.perf_counter() - started) * 1000
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"agent": spec.agent_id, "model": self.model,
                                    "prompt_version": spec.version, "input": payload,
                                    "output": out.model_dump(mode="json"), "tokens": tokens},
                                   indent=1, sort_keys=True, default=str))
        return out, CallRecord(spec.agent_id, self.model, key, False, tokens, latency)
