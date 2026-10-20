"""Project configuration. Secrets come from `.env`; tunable model parameters live here."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "")
LLM_MODE: str = os.getenv("LLM_MODE", "cache_only")
APPROVAL_MODE: str = os.getenv("APPROVAL_MODE", "policy")

DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
RESULTS_DIR = ROOT / "results"

# Confidence gate (PLAN §14.5)
CONFIDENCE_WEIGHTS: dict[str, float] = {
    "consistency": 0.4,
    "margin": 0.3,
    "freshness": 0.2,
    "validator_clean": 0.1,
}
CONFIDENCE_EXECUTE = 0.90
CONFIDENCE_INFO_ROUND = 0.75
CONSISTENCY_SAMPLES = 3
FRESHNESS_ZERO_MIN = 30

# Negotiation and approval
MAX_NEGOTIATION_ROUNDS = 3
POLICY_APPROVAL_DELAY_MIN = 2
R6_DETOUR_MIN = 10

# Partial-information board refresh (PLAN §11)
BOARD_UPDATE_MIN = 15
