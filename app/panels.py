"""Dispatch-console panels (CAD-style): incidents, conversation, hospital and unit boards."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from app.state import TRIAGE, DashState, FeedRow, transport_summary
from eval.handling import by_severity, decision_time, patient_handling

SHIFT_START_HOUR = 14
TRIAGE_COLOR = {"RED": "#E5484D", "YELLOW": "#E6C229", "GREEN": "#3DD68C", "BLACK": "#8B8D98"}
SEVERITY_COLOR = {"CRITICAL": "#E5484D", "SERIOUS": "#F08C2E", "MINOR": "#E6C229",
                  "EXPECTANT": "#8B8D98"}
STATUS_COLOR = {"PENDING": "#E5484D", "UNITS EN ROUTE": "#4C9EFF", "STAGING": "#B18CFF",
                "ON SCENE": "#B18CFF", "TRANSPORTING": "#F2A33A", "CLEARED": "#5B6672"}
HOSPITAL_STATUS_COLOR = {"OPEN": "#3DD68C", "BUSY": "#F2A33A", "SATURATED": "#E5484D"}
UNIT_COLOR = {"IDLE": "#3DD68C", "EN_ROUTE": "#4C9EFF", "STAGING": "#B18CFF",
              "ON_SCENE": "#B18CFF", "LOADING": "#B18CFF", "TRANSPORTING": "#E5484D",
              "WAITING_AT_ER": "#F2A33A", "HANDOVER": "#F2A33A", "RETURNING": "#8B8D98"}
UNIT_LABEL = {"IDLE": "Available", "EN_ROUTE": "En route", "STAGING": "Staging",
              "ON_SCENE": "On scene", "LOADING": "Loading", "TRANSPORTING": "Transporting",
              "WAITING_AT_ER": "At ER door", "HANDOVER": "Handover", "RETURNING": "Returning"}
ROLE = {  # avatar label, color
    "caller": ("911", "#4C9EFF"), "dispatch": ("DSP", "#2EC4B6"), "unit": ("AMB", "#B18CFF"),
    "hospital": ("HOSP", "#3DD68C"), "safety": ("RULES", "#F2A33A"), "police": ("POL", "#7C8CFF"),
    "fire": ("FIRE", "#F08C2E"), "firm": ("PVT", "#C9D3DD"), "system": ("SYS", "#8B8D98"),
}

CSS = """
<style>
.block-container{padding-top:1.2rem;padding-bottom:2rem;max-width:1680px}
.cad-clock{font-family:ui-monospace,Menlo,monospace;font-size:1.55rem;color:#E6EDF3;
  line-height:1.1;text-align:right}
.cad-clock small{display:block;font-size:.72rem;color:#7D8A97;letter-spacing:.06em}
.cad-chips{display:flex;flex-wrap:wrap;gap:.5rem;margin:.2rem 0 .8rem 0}
.cad-chip{border:1px solid rgba(140,160,180,.25);border-radius:.35rem;padding:.3rem .65rem;
  font-size:.82rem;color:#C9D3DD;background:#111A23}
.cad-chip b{font-family:ui-monospace,Menlo,monospace;font-size:1rem;color:#E6EDF3;
  margin-right:.3rem}
.cad-chip.warn{border-color:#E5484D;color:#FFB4B6}
.cad-h{font-size:.72rem;font-weight:700;letter-spacing:.09em;color:#7D8A97;
  text-transform:uppercase;margin:.1rem 0 .4rem 0}
.cad-table{width:100%;border-collapse:collapse;font-size:.82rem}
.cad-table th{font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:#7D8A97;
  text-align:left;font-weight:600;padding:.35rem .4rem;
  border-bottom:1px solid rgba(140,160,180,.25)}
.cad-table td{padding:.4rem .4rem;border-bottom:1px solid rgba(140,160,180,.10);color:#E6EDF3;
  vertical-align:middle}
.cad-table tr.done td{color:#5B6672}
.cad-table tr.focus td{background:rgba(76,158,255,.10)}
.cad-mono{font-family:ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
.cad-stripe{width:4px;padding:0!important}
.cad-pill{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.04em;
  padding:.12rem .45rem;border-radius:.25rem;color:#0B1117;white-space:nowrap}
.cad-tri{display:inline-block;min-width:2.3rem;text-align:center;font-family:ui-monospace,
  Menlo,monospace;font-size:.74rem;font-weight:700;padding:.08rem .3rem;border-radius:.2rem;
  margin-right:.2rem;color:#0B1117}
.cad-sub{color:#7D8A97;font-size:.74rem}
.cad-bar{display:inline-block;width:3.2rem;height:.38rem;background:rgba(140,160,180,.2);
  border-radius:.2rem;vertical-align:middle;margin-left:.35rem;overflow:hidden}
.cad-bar i{display:block;height:100%}
.msg{display:grid;grid-template-columns:2.6rem 1fr;gap:.55rem;padding:.5rem .2rem;
  border-bottom:1px solid rgba(140,160,180,.10)}
.msg .av{width:2.6rem;height:2.6rem;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:.62rem;font-weight:800;letter-spacing:.03em;color:#0B1117}
.msg .hd{font-size:.8rem;color:#C9D3DD;display:flex;gap:.4rem;align-items:baseline;
  flex-wrap:wrap}
.msg .hd b{color:#E6EDF3}
.msg .hd .t{margin-left:auto;font-family:ui-monospace,Menlo,monospace;color:#7D8A97;
  font-size:.74rem}
.msg .tag{font-size:.62rem;font-weight:700;letter-spacing:.05em;padding:.04rem .35rem;
  border-radius:.2rem;border:1px solid currentColor}
.msg .tx{font-size:.88rem;color:#E6EDF3;line-height:1.35;margin-top:.15rem;
  overflow-wrap:anywhere}
.msg.reject .tx{color:#FFB4B6}
.msg.flag .tx{color:#FFD9A0}
.src{font-size:.62rem;font-weight:700;letter-spacing:.03em;padding:.04rem .4rem;
  border-radius:.6rem;white-space:nowrap}
.src.ai{background:rgba(61,214,140,.16);color:#3DD68C;border:1px solid rgba(61,214,140,.5)}
.src.backup{background:rgba(242,163,58,.14);color:#F2A33A;border:1px solid rgba(242,163,58,.5)}
.src.standin,.src.rules{background:rgba(139,141,152,.14);color:#AEB4BD;
  border:1px solid rgba(139,141,152,.45)}
.ai-banner{border-radius:.4rem;padding:.45rem .7rem;margin:.1rem 0 .6rem 0;font-size:.85rem;
  border:1px solid rgba(140,160,180,.25);background:#111A23;color:#C9D3DD}
.ai-banner b{color:#E6EDF3}
.ai-banner.ai{border-color:rgba(61,214,140,.55)}
.side-tiles{display:grid;grid-template-columns:1fr 1fr;gap:.4rem;margin-bottom:.7rem}
.side-tile{background:#111A23;border:1px solid rgba(140,160,180,.18);border-radius:.4rem;
  padding:.4rem .55rem}
.side-tile b{display:block;font-family:ui-monospace,Menlo,monospace;font-size:1.15rem;
  color:#E6EDF3}
.side-tile span{font-size:.7rem;color:#7D8A97}
.legend-row{display:flex;align-items:center;gap:.5rem;font-size:.8rem;color:#C9D3DD;
  padding:.12rem 0}
.legend-row i{display:inline-block;width:.75rem;height:.75rem;flex:none}
.side-h{display:flex;justify-content:space-between;align-items:center;font-size:.82rem;
  color:#E6EDF3;padding:.28rem 0;border-bottom:1px solid rgba(140,160,180,.10)}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def wall_clock(tick: int) -> str:
    total = SHIFT_START_HOUR * 60 + tick
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


def clock_html(tick: int, seconds: int | None = None) -> str:
    """Time of day; in real-time pace the seconds tick too."""
    secs = f'<span style="color:#7D8A97">:{seconds:02d}</span>' if seconds is not None else ""
    return f'<div class="cad-clock">{wall_clock(tick)}{secs}<small>MINUTE {tick}</small></div>'


def status_chips(state: DashState) -> None:
    k = state.kpis
    chips = [
        (k["active_calls"], "active incidents", False),
        (k["waiting_on_scene"], "patients waiting on scene", k["waiting_on_scene"] > 0),
        (k["in_transport"], "in ambulances", False),
        (k["waiting_at_er"], "waiting for an ER bed", k["waiting_at_er"] > 0),
        (k["in_care"], "in care", False),
        (k["deceased"], "died", k["deceased"] > 0),
        (f"{k['free_units']}/{k['units']}", "ambulances free", k["free_units"] == 0),
        (k["saturated"], "hospitals saturated", k["saturated"] > 0),
    ]
    st.markdown('<div class="cad-chips">' + "".join(
        f'<div class="cad-chip{" warn" if warn else ""}"><b>{v}</b>{html.escape(label)}</div>'
        for v, label, warn in chips) + "</div>", unsafe_allow_html=True)


def _pill(text: str, color: str) -> str:
    return f'<span class="cad-pill" style="background:{color}">{html.escape(text)}</span>'


def _triage_chips(triage: dict) -> str:
    out = []
    for color in TRIAGE.values():
        c = triage[color]
        if c["total"]:
            out.append(f'<span class="cad-tri" style="background:{TRIAGE_COLOR[color]}">'
                       f'{c["on_scene"]}/{c["total"]}</span>')
    return "".join(out)


def _units_short(units: list[str]) -> str:
    if not units:
        return "—"
    shown = ", ".join(units[:2])
    return shown + (f' <span class="cad-sub">+{len(units) - 2}</span>' if len(units) > 2 else "")


def _scroll(table_html: str) -> str:
    return f'<div style="overflow-x:auto;max-width:100%">{table_html}</div>'


def incident_table(state: DashState, focus: str | None) -> None:
    st.markdown('<div class="cad-h">Active incidents</div>', unsafe_allow_html=True)
    if not state.incidents:
        st.caption("No calls yet. Press Start; each 911 call appears here.")
        return
    rows = sorted(state.incidents.values(),
                  key=lambda i: (i["status"] == "CLEARED", -i["call_tick"]))
    body = []
    for inc in rows:
        worst = next((s for s in SEVERITY_COLOR if s in inc["severities"]), "MINOR")
        cls = ("done" if inc["status"] == "CLEARED" else "") + \
            (" focus" if inc["id"] == focus else "")
        kind = html.escape(inc["type"].replace("_", " ").title())
        body.append(
            f'<tr class="{cls}"><td class="cad-stripe" style="background:{SEVERITY_COLOR[worst]}">'
            f'</td><td><b>{inc["id"]}</b><div class="cad-sub">{kind} · {inc["grid"]}</div></td>'
            f'<td>{_triage_chips(inc["triage"])}<div class="cad-sub">waiting / total</div></td>'
            f'<td class="cad-mono">{_units_short(inc["units"])}</td>'
            f'<td>{_pill(inc["status"], STATUS_COLOR[inc["status"]])}</td>'
            f'<td class="cad-mono">{inc["elapsed"]}m</td></tr>')
    st.markdown(_scroll('<table class="cad-table"><tr><th></th><th>Incident</th><th>Patients</th>'
                        '<th>Units</th><th>Status</th><th>Age</th></tr>' + "".join(body) +
                        "</table>"), unsafe_allow_html=True)


def _source_chip(r: FeedRow) -> str:
    if r.source == "ai":
        ai = r.ai or {}
        secs = f" · {ai['latency_ms'] / 1000:.1f}s" if ai.get("latency_ms") else ""
        when = " · saved" if ai.get("cache_hit") else secs
        text = f"AI · {ai.get('model', 'LLM')}{when}" if ai else "AI decision"
    else:
        text = {"standin": "offline stand-in · not AI", "backup": "rule backup",
                "rules": "rule-based"}.get(r.source)
    return f'<span class="src {r.source}">{html.escape(text)}</span>' if text else ""


def _message(r: FeedRow) -> str:
    label, color = ROLE.get(r.role, ROLE["system"])
    if r.role == "hospital" and r.sender.startswith("Hospital "):
        label = "H-" + r.sender.split()[-1]
    cls = "reject" if r.category == "reject" else "flag" if r.category == "flag" else ""
    tag_color = {"reject": "#E5484D", "flag": "#F2A33A"}.get(r.category, "#7D8A97")
    return (f'<div class="msg {cls}"><div class="av" style="background:{color}">{label}</div>'
            f'<div><div class="hd"><b>{html.escape(r.sender)}</b><span>→ '
            f'{html.escape(r.recipient)}</span><span class="tag" style="color:{tag_color}">'
            f'{html.escape(r.kind)}</span>{_source_chip(r)}'
            f'<span class="t">{wall_clock(r.tick)}</span></div>'
            f'<div class="tx">{html.escape(r.text)}</div></div></div>')


AGENT_KINDS = {"PRIORITY REPORT", "PROPOSE", "ACCEPT", "COUNTER", "REJECT", "ESCALATE",
               "RESOLVE", "STAFF REQUEST", "STAFF RESPONSE", "MUTUAL AID REQUEST",
               "MUTUAL AID RESPONSE", "NEEDS APPROVAL", "APPROVED", "OVERRIDDEN", "AI NOT USED"}


def conversation(state: DashState, focus: str | None, height: int = 600,
                 agents_only: bool = False) -> None:
    rows = state.threads.get(focus, []) if focus else state.feed
    if agents_only:  # the agents talking to each other, without crews, calls and status
        rows = [r for r in rows if r.source in ("ai", "standin", "backup")
                or r.kind in AGENT_KINDS]
    title = f"Conversation · {focus}" if focus else "Conversation · all incidents"
    st.markdown(f'<div class="cad-h">{html.escape(title)}</div>', unsafe_allow_html=True)
    with st.container(height=height, border=False):
        if not rows:
            st.caption("Messages between the caller, dispatch, ambulances, hospitals and the "
                       "safety rules appear here, newest first.")
        st.markdown("".join(_message(r) for r in reversed(rows[-250:])), unsafe_allow_html=True)


def hospital_type(h: dict) -> str:
    caps = set(h.get("capabilities", []))
    if h.get("owner") == "PRIVATE":
        return "Private · surge contract"
    if h.get("stabilization_only"):
        return "Community · stabilization bay"
    if "TRAUMA_L1" in caps:
        return "Trauma center (L1)"
    if "TRAUMA_L2" in caps:
        return "Trauma center (L2)"
    return "Community"


def _free(h: dict, r: str) -> str:
    tot = h["totals"].get(r, 0)
    if not tot:
        return '<span class="cad-sub">—</span>'
    free = tot - h["occupied"][r]
    frac = h["occupied"][r] / tot
    color = "#E5484D" if free <= 0 else "#F2A33A" if frac >= 0.8 else "#3DD68C"
    return (f'<span class="cad-mono">{free}<span class="cad-sub">/{tot}</span></span>'
            f'<span class="cad-bar"><i style="width:{min(100, round(frac * 100))}%;'
            f'background:{color}"></i></span>')


def hospital_board(state: DashState) -> None:
    st.markdown('<div class="cad-h">Hospital status board (free / total)</div>',
                unsafe_allow_html=True)
    body = []
    for hid, h in sorted(state.hospitals.items()):
        nurses = h["totals"]["nurse_slot"] // 4
        loan = ""
        if h["nurses_loaned_in"] or h["nurses_loaned_out"]:
            loan = (f' <span class="cad-sub">(+{h["nurses_loaned_in"]}/'
                    f'−{h["nurses_loaned_out"]})</span>')
        last = state.hospital_changes.get(hid, [])
        body.append(
            f'<tr><td><b>{html.escape(h.get("name", hid))}</b><div class="cad-sub">'
            f'{hospital_type(h)}</div></td>'
            f'<td>{_pill(h["status"], HOSPITAL_STATUS_COLOR[h["status"]])}</td>'
            f'<td>{_free(h, "er_bed")}</td><td>{_free(h, "ward_bed")}</td>'
            f'<td>{_free(h, "trauma_bay")}</td><td>{_free(h, "surgeon")}</td>'
            f'<td>{_free(h, "or")}</td><td class="cad-mono">{nurses}{loan}</td>'
            f'<td class="cad-mono">{h["incoming"]}</td>'
            f'<td class="cad-mono">{h["ambulances_waiting"]}</td>'
            f'<td class="cad-mono">{h["queue_scenario"]}</td>'
            f'<td class="cad-mono">{h.get("boarding", 0)}</td>'
            f'<td class="cad-sub">{html.escape(last[-1]) if last else "—"}</td></tr>')
    st.markdown(_scroll('<table class="cad-table"><tr><th>Hospital</th><th>Status</th>'
                        '<th>ER beds</th><th>Ward beds</th><th>Trauma bays</th>'
                        '<th>Surgical teams</th><th>ORs</th><th>ED nurses</th><th>Incoming</th>'
                        '<th>At door</th><th>Waiting</th><th>Boarding</th><th>Last change</th>'
                        '</tr>' + "".join(body) + "</table>"), unsafe_allow_html=True)


LEGEND = [  # (shape css, color, label)
    ("border-radius:50%", "#3DD68C", "Hospital (color = board status)"),
    ("border-radius:50%", "#E5484D", "Call (size = victims, X = unsafe scene)"),
    ("transform:rotate(45deg)", "#E6C229", "Ambulance station"),
    ("clip-path:polygon(50% 0,100% 100%,0 100%)", "#4C9EFF", "Ambulance (color = status)"),
    ("height:.15rem;border-radius:0", "#4C9EFF", "Going to call"),
    ("height:.15rem;border-radius:0", "#E5484D", "Transporting to hospital"),
]


# USD per 1M tokens, input / output (OpenAI list prices; an estimate, check before relying on it).
PRICE = {"gpt-4.1-nano": (0.10, 0.40), "gpt-4o-mini": (0.15, 0.60),
         "gpt-4.1-mini": (0.40, 1.60), "gpt-5-nano": (0.05, 0.40)}
AGENT_NAME = {"assessment": "Assessment", "dispatch": "Dispatch", "allocator": "Allocator"}


def _agent_name(agent: str) -> str:
    return AGENT_NAME.get(agent) or ("Hospital " + agent.split(":")[-1]
                                     if agent.startswith("hospital") else agent)


TYPE_COLOR = {"PROPOSE": "#4C9EFF", "ACCEPT": "#3DD68C", "COUNTER": "#F2A33A",
              "REJECT": "#E5484D", "ESCALATE": "#B18CFF", "RESOLVE": "#2EC4B6",
              "STATUS": "#7D8A97"}


def negotiations(threads: list[dict], focus: str | None, height: int = 520) -> None:
    """Each ambulance's negotiation as one thread: proposals, answers, rulings, outcome."""
    shown = [t for t in threads if focus is None or t["incident"] == focus]
    st.markdown(f'<div class="cad-h">Negotiations · {len(shown)} ambulance(s)</div>',
                unsafe_allow_html=True)
    with st.container(height=height, border=False):
        if not shown:
            st.caption("When an ambulance has patients, Dispatch proposes a hospital and the "
                       "hospital agents accept, counter or reject. Each exchange appears here. "
                       "Baselines do not negotiate.")
        for t in reversed(shown):
            out = t["outcome"]
            end = (f'→ <b>Hospital {out["hospital"]}</b> at {wall_clock(out["tick"])} '
                   f'(decided by {out["by"]})' if out else "→ still open")
            rounds = 1 + max((x["round"] or 0 for x in t["turns"] if x["round"] is not None
                              and x["round"] <= 3), default=0)
            body = "".join(
                f'<div class="msg"><div class="av" style="background:'
                f'{TYPE_COLOR.get(x["type"], "#7D8A97")}">{html.escape(x["type"][:4])}</div>'
                f'<div><div class="hd"><b>{html.escape(x["sender"])}</b><span>→ '
                f'{html.escape(x["recipient"])}</span>'
                + _source_chip(FeedRow(x["tick"], x["sender"], x["recipient"], x["type"],
                                       x["text"], "agent", source=x["source"], ai=x["ai"]))
                + f'<span class="t">{wall_clock(x["tick"])}</span></div>'
                f'<div class="tx">{html.escape(x["text"])}</div></div></div>'
                for x in t["turns"])
            st.markdown(
                f'<div style="border:1px solid rgba(140,160,180,.22);border-radius:.45rem;'
                f'padding:.45rem .6rem;margin-bottom:.6rem"><div class="hd" style="font-size:'
                f'.85rem;color:#E6EDF3"><b>{html.escape(t["unit"])}</b> · '
                f'{t["patients"]} patient(s) · {html.escape(t["incident"] or "")} · '
                f'{rounds} round(s) {end}</div>{body}</div>', unsafe_allow_html=True)


NODE_POS = {"Assessment": (-1.6, 1.3), "Dispatch": (0, 0), "Allocator": (1.6, 1.3),
            "Human reviewer": (0, 1.6), "Hospital A": (-1.8, -0.9), "Hospital B": (-0.6, -1.6),
            "Hospital C": (0.6, -1.6), "Hospital D": (1.8, -0.9), "Ambulances": (-2.2, 0.3),
            "Private firm": (2.2, 0.3)}


def talk_graph(counts) -> None:
    """Who talks to whom: one line per pair, thicker for more messages."""
    import plotly.graph_objects as go

    pairs: dict[tuple, int] = {}
    for (a, b), n in counts.items():
        a = "Private firm" if a.startswith("firm") or a == "MedRide" else a
        b = "Private firm" if b.startswith("firm") or b == "MedRide" else b
        if a in NODE_POS and b in NODE_POS and a != b:
            key = tuple(sorted((a, b)))
            pairs[key] = pairs.get(key, 0) + n
    fig = go.Figure()
    top = max(pairs.values(), default=1)
    for (a, b), n in pairs.items():
        (x0, y0), (x1, y1) = NODE_POS[a], NODE_POS[b]
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", hoverinfo="skip",
                                 line=dict(width=1.5 + 7 * n / top, color="rgba(76,158,255,.45)"),
                                 showlegend=False))
        fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=str(n), showarrow=False,
                           font=dict(color="#E6EDF3", size=11), bgcolor="#0B1016")
    used = {x for pair in pairs for x in pair} or {"Dispatch"}
    names = [n for n in NODE_POS if n in used]
    color = {"Dispatch": "#2EC4B6", "Assessment": "#4C9EFF", "Allocator": "#B18CFF",
             "Human reviewer": "#F2A33A", "Ambulances": "#8B8D98", "Private firm": "#C9D3DD"}
    fig.add_trace(go.Scatter(
        x=[NODE_POS[n][0] for n in names], y=[NODE_POS[n][1] for n in names],
        mode="markers+text", text=names, textposition="bottom center", showlegend=False,
        marker=dict(size=34, color=[color.get(n, "#3DD68C") for n in names],
                    line=dict(color="#0B1016", width=2)),
        textfont=dict(color="#C9D3DD", size=11), hoverinfo="text"))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10),
                      plot_bgcolor="#0B1016", paper_bgcolor="#0B1016",
                      xaxis=dict(visible=False, range=[-2.8, 2.8], fixedrange=True),
                      yaxis=dict(visible=False, range=[-2.1, 2.0], fixedrange=True))
    st.markdown('<div class="cad-h">Who talks to whom (messages so far)</div>',
                unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def run_results(events) -> None:
    """Scorecard of the run so far, and all saved runs side by side."""
    from eval.run_report import SCORECARD, _fmt, load_index, scorecard

    if not events or events[-1].tick < 1:
        st.caption("Start a run to see how well it is being handled.")
    else:
        card = scorecard(events)
        h, d = card["headline"], card["decisions"]
        rows = [{"Measure": label, "Value": _fmt(h.get(key), unit)}
                for label, key, unit in SCORECARD]
        rows += [{"Measure": "Decisions by AI agents", "Value": str(d["ai"])},
                 {"Measure": "Decisions by the rule backup", "Value": str(d["rule_backup"])}]
        st.markdown(f'<div class="cad-h">This run so far · minute {card["minutes"]} · '
                    f'{html.escape(str(card["policy"]))}</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    saved = load_index()
    if saved:
        st.markdown(f'<div class="cad-h">Saved runs ({len(saved)}) · results/runs_saved/'
                    f'index.csv</div>', unsafe_allow_html=True)
        cols = ["saved", "incident", "policy", "model", "deaths", "critical_on_time",
                "critical_care_mean", "response_mean", "er_wait_over_base", "rejections",
                "ai_decisions", "rule_backup_decisions", "llm_tokens", "folder"]
        st.dataframe(pd.DataFrame(saved)[cols][::-1], hide_index=True,
                     use_container_width=True, height=240)


def ai_banner(state: DashState, policy: str) -> None:
    """One line saying who makes the decisions, and how many came from AI vs the backup."""
    k = state.kpis
    if "agents" not in policy.lower():
        line, cls = f"<b>{html.escape(policy)}</b>: fixed rules, no AI agents.", ""
    elif "offline" in policy.lower():
        line, cls = ("<b>Offline stand-in</b>: the agents are played by simple rules so the "
                     "app works without OpenAI. This is not AI."), ""
    else:
        models = sorted({c["model"] for c in state.ai_calls}) or ["GPT"]
        saved = sum(1 for c in state.ai_calls if c.get("cache_hit"))
        line = (f"<b>Live AI agents ({html.escape(', '.join(models))})</b>: "
                f"{len(state.ai_calls)} AI calls so far"
                + (f", {saved} replayed from saved answers (free)" if saved else "")
                + f". Decisions by AI <b>{k['ai_decisions']}</b> · by rule backup "
                  f"<b>{k['backup_decisions']}</b>.")
        cls = "ai"
    st.markdown(f'<div class="ai-banner {cls}">{line}</div>', unsafe_allow_html=True)


def ai_activity(state: DashState) -> None:
    """Every LLM call: summary, table, and the exact input and answer of a chosen call."""
    import json

    from orca_agents.llm_cache import CACHE_DIR

    calls = state.ai_calls
    if not calls:
        st.caption("No AI calls in this run. Pick an \"AI agents\" option to see them here.")
        return
    tokens = sum(c.get("tokens", 0) for c in calls)
    live = [c for c in calls if not c.get("cache_hit")]
    model = calls[0]["model"]
    p_in, p_out = PRICE.get(model, (0.15, 0.60))
    cost = sum(c.get("tokens", 0) for c in live) * (0.9 * p_in + 0.1 * p_out) / 1e6
    k = state.kpis
    st.markdown(
        f'<div class="ai-banner">{len(calls)} AI calls · {tokens:,} tokens · '
        f'{len(calls) - len(live)} replayed free · about ${cost:.3f} for the live calls '
        f'(estimate) · decisions by AI {k["ai_decisions"]}, by rule backup '
        f'{k["backup_decisions"]}</div>', unsafe_allow_html=True)
    rows = [{"Minute": c["tick"], "Time": wall_clock(c["tick"]),
             "Agent": _agent_name(c["agent"]), "Model": c["model"],
             "Tokens": c.get("tokens", 0),
             "Seconds": round(c.get("latency_ms", 0) / 1000, 1) if not c.get("cache_hit")
             else None, "Answer": "saved (replay)" if c.get("cache_hit") else "live"}
            for c in calls]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=260)
    labels = [f"{r['Time']} · {r['Agent']} · {c['key'][:8]}"
              for r, c in zip(rows, calls, strict=True)]
    pick = st.selectbox("Open an AI call to see exactly what the agent saw and answered",
                        range(len(calls)), index=len(calls) - 1,
                        format_func=lambda i: labels[i], key="ai_call_pick")
    c = calls[pick]
    path = CACHE_DIR / c["agent"].replace(":", "_") / f"{c['key']}.json"
    if not path.exists():
        st.caption("The saved answer for this call is not on this machine.")
        return
    rec = json.loads(path.read_text())
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="cad-h">What the agent was given</div>',
                    unsafe_allow_html=True)
        st.json(rec.get("input", {}), expanded=1)
    with right:
        st.markdown('<div class="cad-h">What the agent answered</div>', unsafe_allow_html=True)
        if "error" in rec:
            st.error(f"No usable answer: {rec['error']}")
        else:
            st.json(rec.get("output", {}), expanded=True)
        st.caption(f"Model {rec.get('model')} · prompt version {rec.get('prompt_version')} · "
                   f"{rec.get('tokens', 0)} tokens")


def map_sidebar(state: DashState, town_population: int, area_km: float) -> set[str]:
    """Left panel beside the map: town facts, layer toggles, legend, hospitals. Returns layers."""
    from app.map_view import LAYERS

    units = [u for u in state.units.values() if u.get("activated")]
    homes = {tuple(u["home"]) for u in units if u.get("home")}
    tiles = [(f"{town_population:,}", "residents"), (len(state.hospitals), "hospitals"),
             (len(units), "ambulances on duty"), (len(homes), "stations"),
             (f"{area_km * area_km:.0f}", "km² town"), (state.kpis["active_calls"], "active calls")]
    st.markdown('<div class="side-tiles">' + "".join(
        f'<div class="side-tile"><b>{v}</b><span>{html.escape(str(label))}</span></div>'
        for v, label in tiles) + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="cad-h">Layers</div>', unsafe_allow_html=True)
    layers = {name for name in LAYERS if st.toggle(name, value=True, key=f"layer_{name}")}
    st.markdown('<div class="cad-h" style="margin-top:.6rem">Legend</div>' + "".join(
        f'<div class="legend-row"><i style="background:{c};{shape}"></i>{html.escape(t)}</div>'
        for shape, c, t in LEGEND), unsafe_allow_html=True)
    st.markdown('<div class="cad-h" style="margin-top:.7rem">Hospitals</div>' + "".join(
        f'<div class="side-h"><span><b>{hid}</b> · {html.escape(hospital_type(h))}</span>'
        f'{_pill(h["status"], HOSPITAL_STATUS_COLOR[h["status"]])}</div>'
        for hid, h in sorted(state.hospitals.items())), unsafe_allow_html=True)
    return layers


def unit_board(state: DashState) -> None:
    body = []
    for u in sorted(state.units.values(), key=lambda u: u["id"]):
        if not u.get("activated"):
            body.append(f'<tr class="done"><td><b>{u["id"]}</b></td><td>{u["unit_type"]}</td>'
                        f'<td>{_pill("Standby", "#5B6672")}</td><td colspan="3" '
                        'class="cad-sub">private unit, activated only through mutual aid</td>'
                        '</tr>')
            continue
        state_pill = _pill(UNIT_LABEL.get(u["state"], u["state"]),
                           UNIT_COLOR.get(u["state"], "#8B8D98"))
        dest = f"Hospital {u['hospital_id']}" if u.get("hospital_id") else "—"
        body.append(
            f'<tr><td><b>{u["id"]}</b></td><td>{u["unit_type"]}</td><td>{state_pill}</td>'
            f'<td class="cad-mono">{u.get("incident_id") or "—"}</td>'
            f'<td class="cad-mono">{dest}</td>'
            f'<td class="cad-mono">{u["minutes_in_status"]}m</td></tr>')
    st.markdown('<table class="cad-table"><tr><th>Unit</th><th>Type</th><th>Status</th>'
                '<th>Incident</th><th>Destination</th><th>In status</th></tr>'
                + "".join(body) + "</table>", unsafe_allow_html=True)


def mci_board(state: DashState) -> None:
    mcis = [i for i in state.incidents.values() if i["victims"] > 3]
    if not mcis:
        st.caption("No mass-casualty incident in this run.")
        return
    for inc in mcis:
        kind = inc["type"].replace("_", " ").title()
        st.markdown(f'<div class="cad-h">{inc["id"]} · {kind} · {inc["victims"]} victims '
                    f'(caller reported {inc["reported"]})</div>', unsafe_allow_html=True)
        left, right = st.columns(2, gap="large")
        rows = "".join(
            f'<tr><td><span class="cad-tri" style="background:{TRIAGE_COLOR[c]}">{c}</span></td>'
            f'<td class="cad-mono">{v["total"]}</td><td class="cad-mono">{v["on_scene"]}</td>'
            f'<td class="cad-mono">{v["transport"]}</td><td class="cad-mono">{v["hospital"]}</td>'
            f'<td class="cad-mono">{v["died"]}</td></tr>'
            for c, v in inc["triage"].items() if v["total"])
        left.markdown('<table class="cad-table"><tr><th>Triage</th><th>Total</th>'
                      '<th>On scene</th><th>In transport</th><th>At hospital</th><th>Died</th>'
                      '</tr>' + rows + "</table>", unsafe_allow_html=True)
        summary = transport_summary(state, inc["id"])
        if summary:
            rows = "".join(
                f'<tr><td><b>Hospital {hid}</b></td>' + "".join(
                    f'<td class="cad-mono">{counts[c]}</td>' for c in TRIAGE.values()) +
                f'<td class="cad-mono">{sum(counts.values())}</td></tr>'
                for hid, counts in summary.items())
            right.markdown('<table class="cad-table"><tr><th>Sent to</th><th>Red</th>'
                           '<th>Yellow</th><th>Green</th><th>Black</th><th>Total</th></tr>' +
                           rows + "</table>", unsafe_allow_html=True)
        else:
            right.caption("No patients have reached a hospital yet.")


def timeline(state: DashState, events, timings, focus: str | None) -> None:
    if not state.handling:
        st.caption("Handling times appear once calls arrive.")
        return
    rows = {r["incident_id"]: r for r in state.handling}
    if focus and focus in rows:
        r = rows[focus]

        def m(v):
            return "—" if v is None else f"{v} min"

        cols = st.columns(5)
        cols[0].metric("Call → dispatch", m(r["decision_min"]))
        cols[1].metric("Call → on scene", m(r["scene_min"]))
        cols[2].metric("Call → hospital", m(r["hospital_min"]))
        cols[3].metric("Call → care (avg)", m(r["care_mean_min"]))
        cols[4].metric("Patients in care", f"{r['in_care']}/{r['victims']}")
    df = pd.DataFrame(state.handling)[[
        "incident_id", "type", "call_tick", "victims", "decision_min", "scene_min",
        "hospital_min", "care_mean_min", "care_max_min", "in_care", "deceased", "rejections"]]
    df.columns = ["Incident", "Type", "Called (min)", "Victims", "→ dispatch", "→ scene",
                  "→ hospital", "→ care avg", "→ care max", "In care", "Died", "Blocked"]
    st.dataframe(df, hide_index=True, use_container_width=True)
    sev = pd.DataFrame(by_severity(patient_handling(events)))
    if not sev.empty:
        st.markdown("**Call to definitive care by severity** (simulated minutes)")
        st.dataframe(sev, hide_index=True, use_container_width=True)
    d = decision_time(timings, events)
    st.caption(f"Real decision time: {d['decisions']} decisions, {d['total_ms']:.0f} ms total "
               f"({d['mean_ms_per_decision']:.2f} ms each). LLM calls: {d['llm_calls']}, "
               f"tokens: {d['tokens']}.")
