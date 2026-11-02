"""ORCA-EMS Dashboard v2 — premium panels.

Design goals
────────────
• Works offline: scripted backend, no OpenAI key required.
• Non-technical: every piece of jargon is translated to plain English.
• Futuristic mission-control aesthetic with Google Fonts + glassmorphism.
• Shows AI reasoning as a story, not raw log lines.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard_v2.state import TRIAGE, DashState, FeedRow, transport_summary  # noqa: E402
from eval.handling import by_severity, decision_time, patient_handling  # noqa: E402

SHIFT_START_HOUR = 14

# ── colour palettes ────────────────────────────────────────────────────────────
SEVERITY_COLOR = {
    "CRITICAL": "#FF4757", "SERIOUS": "#FFA502",
    "MINOR": "#2ED573", "EXPECTANT": "#747D8C",
}
TRIAGE_COLOR = {
    "RED": "#FF4757", "YELLOW": "#FFA502",
    "GREEN": "#2ED573", "BLACK": "#747D8C",
}
STATUS_COLOR = {
    "PENDING": "#FF4757", "UNITS EN ROUTE": "#4C9EFF",
    "STAGING": "#B18CFF", "ON SCENE": "#B18CFF",
    "TRANSPORTING": "#FFA502", "CLEARED": "#3A4A5A",
}
HOSPITAL_STATUS_COLOR = {"OPEN": "#2ED573", "BUSY": "#FFA502", "SATURATED": "#FF4757"}
UNIT_COLOR = {
    "IDLE": "#2ED573", "EN_ROUTE": "#4C9EFF", "STAGING": "#B18CFF",
    "ON_SCENE": "#B18CFF", "LOADING": "#B18CFF", "TRANSPORTING": "#FF4757",
    "WAITING_AT_ER": "#FFA502", "HANDOVER": "#FFA502", "RETURNING": "#5B6672",
}
UNIT_LABEL = {
    "IDLE": "Available", "EN_ROUTE": "En route to scene",
    "STAGING": "Staging (unsafe scene)", "ON_SCENE": "On scene",
    "LOADING": "Loading patient", "TRANSPORTING": "Transporting to hospital",
    "WAITING_AT_ER": "Waiting at ER door", "HANDOVER": "Handing over",
    "RETURNING": "Returning to station",
}
ROLE = {
    "caller": ("911", "#4C9EFF"), "dispatch": ("AI", "#2EC4B6"),
    "unit": ("AMB", "#B18CFF"), "hospital": ("HOSP", "#3DD68C"),
    "safety": ("RULE", "#FFA502"), "police": ("POL", "#7C8CFF"),
    "fire": ("FIRE", "#F08C2E"), "firm": ("PVT", "#C9D3DD"),
    "system": ("SYS", "#5B6672"),
}

# ── plain-English story translation ──────────────────────────────────────────
KIND_TITLE: dict[str, str] = {
    "911 CALL": "Emergency call received",
    "ORDER": "Ambulance dispatched",
    "SCENE REPORT": "First responders on scene — reporting injuries",
    "SCENE SECURE": "Police secured the scene — ambulances can move in",
    "PROPOSE": "AI checking if hospital has space…",
    "ACCEPT": "✅ Hospital confirmed — space available",
    "COUNTER": "🔄 Hospital: can only take some patients",
    "REJECT": "❌ Hospital full or wrong type for this patient",
    "RESOLVE": "✅ AI resolved the standoff",
    "ESCALATE": "⏸ AI escalating — situation needs arbitration",
    "NEEDS APPROVAL": "⏸ Waiting for human review",
    "APPROVED": "✅ Decision approved",
    "OVERRIDDEN": "↩ Reviewer changed the decision",
    "IN CARE": "🏥 Patient now receiving treatment",
    "WALK-IN": "🚶 Patient walked to hospital on their own",
    "STAFF": "👩‍⚕️ Nurses transferred between hospitals",
    "MUTUAL AID": "🆘 Private ambulances called in",
    "STAFF REQUEST": "📤 Hospital requesting extra nurses",
    "STAFF RESPONSE": "📥 Hospital sending nurses",
    "PRE ALERT": "📡 Hospital notified — ambulance on its way",
    "CAUTION": "⚠️ Safety note",
    "REVIEW": "⏸ Human review required",
    "DIED": "💔 Patient did not survive",
    "ALERT": "🔔 Alert",
    "ALERT CLEARED": "✅ Alert cleared",
    "FALLBACK USED": "⚡ AI unavailable — backup rules used",
    "PRIORITY REPORT": "🧠 AI completed emergency assessment",
    "MUTUAL AID REQUEST": "🆘 Private ambulances requested",
    "MUTUAL AID RESPONSE": "✅ Private ambulance confirmed",
    "BLOCKED R1": "🚫 Safety: that unit cannot take this order right now",
    "BLOCKED R2": "🚫 Safety: hospital won't have space when the ambulance arrives",
    "BLOCKED R3": "🚫 Safety: critical trauma needs a trauma center, not this hospital",
    "BLOCKED R4": "🚫 Safety: private hospital contract doesn't allow this",
    "BLOCKED R5": "⚠️ Scene not yet safe — unit will wait nearby",
    "BLOCKED R6": "⚠️ Risky route — flagged for human review",
    "BLOCKED R7": "🚫 Safety: a critical patient must travel alone",
    "BLOCKED R8": "🚫 Safety: lending those nurses would leave hospital understaffed",
    "BLOCKED R9": "🚫 Safety: AI tried to take an unauthorised action",
}

AGENT_PLAIN: dict[str, str] = {
    "assessment": "Analysed the emergency call",
    "dispatch": "Planned which ambulances go where and which hospital",
    "allocator": "Resolved a conflict or deadlocked negotiation",
    "hospital": "Hospital decided whether to accept patients",
}

AGENT_COLOR: dict[str, str] = {
    "assessment": "#4C9EFF",
    "dispatch":   "#2EC4B6",
    "allocator":  "#B18CFF",
    "hospital":   "#3DD68C",
}

STORY_DOT: dict[str, str] = {
    "call": "dot-call", "decision": "dot-dispatch",
    "agent": "dot-ai",  "reject": "dot-block",
    "flag": "dot-review", "unit": "dot-unit",
    "hospital": "dot-hospital", "patient": "dot-patient",
    "alert": "dot-alert", "system": "dot-system",
}

# ── premium CSS ───────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

.block-container{padding-top:.5rem!important;padding-bottom:2rem;max-width:1820px!important;font-family:'Inter',-apple-system,sans-serif}

/* ── KPI strip ── */
.kpi-strip{display:grid;grid-template-columns:repeat(8,1fr);gap:.5rem;margin-bottom:.8rem}
.kpi-tile{background:linear-gradient(135deg,rgba(255,255,255,.04),rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.08);border-radius:.6rem;padding:.6rem .75rem;
  position:relative;overflow:hidden;transition:border-color .2s}
.kpi-tile:hover{border-color:rgba(76,158,255,.35)}
.kpi-tile.warn{border-color:rgba(255,71,87,.4)}
.kpi-tile.warn .kpi-n{color:#FF4757}
.kpi-tile::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
  background:var(--kl,rgba(76,158,255,.35));border-radius:0 0 .6rem .6rem}
.kpi-tile.warn::after{--kl:rgba(255,71,87,.5)}
.kpi-n{font-family:'JetBrains Mono',monospace;font-size:1.6rem;font-weight:600;
  color:#E6EDF3;line-height:1.1}
.kpi-label{font-size:.6rem;font-weight:500;letter-spacing:.08em;text-transform:uppercase;
  color:#4A5A6A;margin-top:.18rem}
.kpi-icon{position:absolute;right:.6rem;top:.45rem;font-size:1rem;opacity:.3}

/* ── Story timeline ── */
.story-wrap{position:relative;padding-left:2rem}
.story-line{position:absolute;left:.55rem;top:.8rem;bottom:0;width:1px;
  background:linear-gradient(to bottom,rgba(76,158,255,.35),rgba(255,255,255,.03))}
.story-row{position:relative;padding:.45rem 0 .45rem .6rem;
  border-bottom:1px solid rgba(255,255,255,.04);transition:background .12s}
.story-row:hover{background:rgba(255,255,255,.02);border-radius:.4rem}
.story-dot{position:absolute;left:-1.45rem;top:.65rem;width:1.1rem;height:1.1rem;
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:.5rem;font-weight:800;color:#07111e;
  box-shadow:0 0 7px var(--dg,rgba(76,158,255,.5))}
.story-time{font-family:'JetBrains Mono',monospace;font-size:.6rem;color:#3A4A5A;margin-bottom:.08rem}
.story-title{font-size:.82rem;font-weight:600;color:#C9D3DD;line-height:1.3}
.story-body{font-size:.76rem;color:#7D8A97;margin-top:.1rem;line-height:1.4}
.story-body b{color:#9AB0C0}
.story-body em{color:#FFA502;font-style:normal}
/* dot colours */
.dot-call{background:#4C9EFF;--dg:rgba(76,158,255,.6)}
.dot-ai{background:#B18CFF;--dg:rgba(177,140,255,.6)}
.dot-dispatch{background:#2EC4B6;--dg:rgba(46,196,182,.6)}
.dot-hospital{background:#3DD68C;--dg:rgba(61,214,140,.6)}
.dot-unit{background:#FFA502;--dg:rgba(255,165,2,.6)}
.dot-patient{background:#3DD68C;--dg:rgba(61,214,140,.5)}
.dot-alert{background:#FF4757;--dg:rgba(255,71,87,.6)}
.dot-block{background:#FF4757;--dg:rgba(255,71,87,.6)}
.dot-review{background:#FFA502;--dg:rgba(255,165,2,.6)}
.dot-system{background:#3A4A5A;--dg:rgba(58,74,90,.4)}

/* ── Hospital cards ── */
.hosp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.6rem}
.hosp-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
  border-radius:.6rem;padding:.85rem;position:relative;overflow:hidden;
  transition:box-shadow .2s,border-color .2s}
.hosp-card:hover{box-shadow:0 0 20px rgba(76,158,255,.07);border-color:rgba(76,158,255,.2)}
.hosp-top{position:absolute;top:0;left:0;right:0;height:3px;background:var(--ha,#3DD68C)}
.hosp-name{font-weight:700;font-size:.95rem;color:#E6EDF3;margin-top:.1rem}
.hosp-type{font-size:.68rem;color:#4A5A6A;margin-bottom:.55rem}
.hosp-pill{display:inline-block;font-size:.6rem;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;padding:.1rem .45rem;border-radius:1rem;margin-bottom:.55rem}
.res-row{display:flex;align-items:center;gap:.45rem;margin-bottom:.28rem}
.res-name{font-size:.66rem;color:#4A5A6A;width:5.5rem;flex-shrink:0}
.res-track{flex:1;height:5px;background:rgba(255,255,255,.07);border-radius:3px;overflow:hidden}
.res-fill{height:100%;border-radius:3px;transition:width .4s}
.res-num{font-family:'JetBrains Mono',monospace;font-size:.68rem;color:#C9D3DD;width:3rem;text-align:right}
.hosp-footer{display:flex;gap:.6rem;margin-top:.5rem;padding-top:.42rem;
  border-top:1px solid rgba(255,255,255,.06);font-size:.7rem;color:#4A5A6A;flex-wrap:wrap}
.hosp-footer b{color:#9AB0C0}
.hosp-cap{font-size:.65rem;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);
  border-radius:.25rem;padding:.07rem .3rem;color:#7D8A97;margin-right:.2rem}

/* ── AI decision cards ── */
.ai-card{background:rgba(177,140,255,.04);border:1px solid rgba(177,140,255,.12);
  border-radius:.5rem;padding:.65rem .8rem;margin-bottom:.4rem;position:relative;overflow:hidden}
.ai-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;
  background:var(--aa,#B18CFF)}
.ai-header{display:flex;align-items:center;gap:.45rem;margin-bottom:.28rem;flex-wrap:wrap}
.ai-badge{font-size:.58rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  padding:.1rem .38rem;border-radius:.2rem}
.ai-time{font-family:'JetBrains Mono',monospace;font-size:.66rem;color:#3A4A5A;margin-left:auto}
.ai-toks{font-size:.68rem;color:#4A5A6A}
.cache-hit{font-size:.57rem;font-weight:600;padding:.05rem .28rem;border-radius:.2rem;
  background:rgba(61,214,140,.12);color:#3DD68C;border:1px solid rgba(61,214,140,.25)}
.cache-live{font-size:.57rem;font-weight:600;padding:.05rem .28rem;border-radius:.2rem;
  background:rgba(76,158,255,.1);color:#4C9EFF;border:1px solid rgba(76,158,255,.2)}
.ai-desc{font-size:.8rem;color:#9AB0C0;line-height:1.35}
/* confidence */
.conf-row{display:flex;align-items:center;gap:.5rem;font-size:.67rem;color:#4A5A6A;margin-top:.12rem}
.conf-track{flex:1;height:4px;background:rgba(255,255,255,.07);border-radius:2px;overflow:hidden}
.conf-fill{height:100%;border-radius:2px}
.conf-val{font-family:'JetBrains Mono',monospace;font-size:.7rem;font-weight:600}
.conf-action{font-size:.58rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  padding:.06rem .3rem;border-radius:.18rem;margin-left:.25rem}

/* ── Neg pills ── */
.neg-pill{display:inline-flex;align-items:center;font-size:.6rem;font-weight:700;
  letter-spacing:.04em;padding:.1rem .38rem;border-radius:.25rem;margin:.08rem .08rem}
.np-accept{background:rgba(46,213,115,.14);color:#2ED573;border:1px solid rgba(46,213,115,.28)}
.np-reject{background:rgba(255,71,87,.14);color:#FF4757;border:1px solid rgba(255,71,87,.28)}
.np-counter{background:rgba(255,165,2,.14);color:#FFA502;border:1px solid rgba(255,165,2,.28)}
.np-propose{background:rgba(76,158,255,.12);color:#4C9EFF;border:1px solid rgba(76,158,255,.22)}
.np-resolve{background:rgba(177,140,255,.14);color:#B18CFF;border:1px solid rgba(177,140,255,.28)}
.np-escalate{background:rgba(255,165,2,.14);color:#FFA502;border:1px solid rgba(255,165,2,.28)}

/* ── Unit cards ── */
.unit-grid{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.3rem}
.unit-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
  border-radius:.5rem;padding:.5rem .7rem;min-width:148px;position:relative;overflow:hidden}
.unit-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
  background:var(--ua,#3DD68C)}
.unit-id{font-family:'JetBrains Mono',monospace;font-size:.8rem;font-weight:600;color:#E6EDF3}
.unit-state-pill{display:inline-block;font-size:.62rem;font-weight:600;padding:.1rem .35rem;
  border-radius:.2rem;margin-top:.15rem;white-space:nowrap}
.unit-dest{font-size:.68rem;color:#4A5A6A;margin-top:.1rem;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;max-width:130px}

/* ── Messages ── */
.msg{display:grid;grid-template-columns:2.2rem 1fr;gap:.5rem;padding:.5rem .25rem;
  border-bottom:1px solid rgba(255,255,255,.05);transition:background .12s}
.msg:hover{background:rgba(255,255,255,.02)}
.msg .av{width:2.2rem;height:2.2rem;border-radius:.35rem;display:flex;align-items:center;
  justify-content:center;font-size:.55rem;font-weight:800;color:#07111e;flex-shrink:0}
.msg .hd{font-size:.76rem;color:#C9D3DD;display:flex;gap:.35rem;align-items:baseline;flex-wrap:wrap}
.msg .hd b{color:#E6EDF3;font-weight:600}
.msg .hd .t{margin-left:auto;font-family:'JetBrains Mono',monospace;color:#3A4A5A;font-size:.68rem}
.msg .tag{font-size:.58rem;font-weight:700;letter-spacing:.06em;padding:.04rem .28rem;
  border-radius:.18rem;border:1px solid currentColor;text-transform:uppercase}
.msg .tx{font-size:.83rem;color:#C9D3DD;line-height:1.4;margin-top:.1rem}
.msg.reject .tx{color:#FF8A8D}
.msg.flag .tx{color:#FFD9A0}

/* ── Misc ── */
.v2-clock{font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:600;
  color:#E6EDF3;text-align:right;line-height:1.1;letter-spacing:.03em}
.v2-clock small{display:block;font-size:.58rem;color:#3A4A5A;letter-spacing:.12em;text-transform:uppercase}
.v2-h{font-size:.6rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  color:#3A4A5A;margin:.15rem 0 .5rem 0;padding-bottom:.3rem;
  border-bottom:1px solid rgba(255,255,255,.06);display:flex;align-items:center;gap:.4rem}
.v2-h::before{content:'';flex:none;width:2px;height:.65rem;background:#4C9EFF;border-radius:1px}
.legend-row{display:flex;align-items:center;gap:.45rem;font-size:.76rem;color:#C9D3DD;padding:.1rem 0}
.legend-row i{display:inline-block;width:.72rem;height:.72rem;flex:none}
.side-tiles{display:grid;grid-template-columns:1fr 1fr;gap:.4rem;margin-bottom:.6rem}
.side-tile{background:rgba(255,255,255,.03);border:1px solid rgba(140,160,180,.1);
  border-radius:.4rem;padding:.38rem .5rem}
.side-tile b{display:block;font-family:'JetBrains Mono',monospace;font-size:1.1rem;color:#E6EDF3}
.side-tile span{font-size:.68rem;color:#7D8A97}
.side-h{display:flex;justify-content:space-between;align-items:center;font-size:.8rem;
  color:#E6EDF3;padding:.25rem 0;border-bottom:1px solid rgba(255,255,255,.06)}
.cad-h{font-size:.72rem;font-weight:700;letter-spacing:.09em;color:#7D8A97;
  text-transform:uppercase;margin:.1rem 0 .4rem 0}
.cad-table{width:100%;border-collapse:collapse;font-size:.82rem}
.cad-table th{font-size:.66rem;letter-spacing:.06em;text-transform:uppercase;color:#7D8A97;
  text-align:left;font-weight:600;padding:.32rem .4rem;border-bottom:1px solid rgba(140,160,180,.12)}
.cad-table td{padding:.38rem .4rem;border-bottom:1px solid rgba(140,160,180,.06);
  color:#E6EDF3;vertical-align:middle}
.cad-table tr.done td{color:#3A4A5A}
.cad-table tr.focus td{background:rgba(76,158,255,.07)}
.cad-mono{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums}
.cad-stripe{width:3px;padding:0!important}
.cad-pill{display:inline-block;font-size:.66rem;font-weight:700;letter-spacing:.04em;
  padding:.1rem .42rem;border-radius:.22rem;color:#07111e;white-space:nowrap}
.cad-tri{display:inline-block;min-width:2.2rem;text-align:center;
  font-family:'JetBrains Mono',monospace;font-size:.72rem;font-weight:700;
  padding:.07rem .28rem;border-radius:.18rem;margin-right:.18rem;color:#07111e}
.cad-sub{color:#7D8A97;font-size:.72rem}
.cad-bar{display:inline-block;width:3rem;height:.35rem;background:rgba(140,160,180,.18);
  border-radius:.2rem;vertical-align:middle;margin-left:.3rem;overflow:hidden}
.cad-bar i{display:block;height:100%}
.compare-win{background:rgba(46,213,115,.08);border:1px solid rgba(46,213,115,.2);
  border-radius:.4rem;padding:.3rem .5rem;text-align:center}
.compare-cell{text-align:center;font-family:'JetBrains Mono',monospace}
</style>
"""

# ── helpers ───────────────────────────────────────────────────────────────────

def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f"<style>{Path(__file__).with_name('styles.css').read_text()}</style>",
                unsafe_allow_html=True)


def wall_clock(tick: int) -> str:
    total = SHIFT_START_HOUR * 60 + tick
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


def clock_html(tick: int) -> str:
    return (f'<div class="v2-clock">{wall_clock(tick)}'
            f'<small>MINUTE&nbsp;{tick}</small></div>')


def _pill(text: str, color: str) -> str:
    return (f'<span class="cad-pill" style="background:{color}">'
            f'{html.escape(str(text))}</span>')


def _scroll(inner: str) -> str:
    return f'<div style="overflow-x:auto;max-width:100%">{inner}</div>'


def _triage_chips(triage: dict) -> str:
    out = []
    for color, hex_c in TRIAGE_COLOR.items():
        c = triage[color]
        if c["total"]:
            out.append(
                f'<span class="cad-tri" style="background:{hex_c}">'
                f'{c["on_scene"]}/{c["total"]}</span>'
            )
    return "".join(out)


def _units_short(units: list[str]) -> str:
    if not units:
        return "—"
    shown = ", ".join(units[:2])
    return shown + (f' <span class="cad-sub">+{len(units) - 2}</span>'
                    if len(units) > 2 else "")


# ── KPI strip ─────────────────────────────────────────────────────────────────

def kpi_bar(state: DashState) -> None:
    k = state.kpis
    tiles = [
        ("Active calls",      k["active_calls"],      False, "📡"),
        ("Waiting on scene",  k["waiting_on_scene"],  k["waiting_on_scene"] > 0, "🏔️"),
        ("In ambulances",     k["in_transport"],       False, "🚑"),
        ("Reached care",      k["in_care"],            False, "🏥"),
        ("Deaths",            k["deceased"],           k["deceased"] > 0, "💔"),
        ("Ambulances free",   f"{k['free_units']}/{k['units']}", k["free_units"] == 0, "🔑"),
        ("Waiting at ER",     k["waiting_at_er"],      k["waiting_at_er"] > 0, "⏳"),
        ("Reviews raised",    k["escalations"],        False, "👤"),
    ]
    html_parts = ['<div class="kpi-strip">']
    for label, val, warn, icon in tiles:
        cls = "kpi-tile warn" if warn else "kpi-tile"
        html_parts.append(
            f'<div class="{cls}">'
            f'<div class="kpi-icon">{icon}</div>'
            f'<div class="kpi-n">{val}</div>'
            f'<div class="kpi-label">{html.escape(label)}</div>'
            f'</div>'
        )
    html_parts.append('</div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)


# ── status chips (compat) ─────────────────────────────────────────────────────

def status_chips(state: DashState) -> None:
    kpi_bar(state)


# ── WHAT'S HAPPENING — plain-English story panel ──────────────────────────────

def _story_row(row: FeedRow) -> str:
    dot = STORY_DOT.get(row.category, "dot-system")
    title = KIND_TITLE.get(row.kind, row.kind.replace("_", " ").title())
    sender_info = f"<b>{html.escape(row.sender)}</b> → {html.escape(row.recipient)}"
    source = {"ai": "AI agent", "standin": "Scripted agent", "backup": "Rule backup",
              "rules": "Rule policy", "sim": "Simulation"}.get(row.source, "Simulation")

    # Translate raw text into plain English where possible
    body = html.escape(row.text)

    # Make severity words pop
    for sev, col in SEVERITY_COLOR.items():
        body = body.replace(
            html.escape(sev),
            f'<em style="color:{col};font-weight:600">{sev}</em>',
        )

    return (
        f'<div class="story-row">'
        f'  <div class="story-dot {dot}">●</div>'
        f'  <div class="story-time">{wall_clock(row.tick)} · {source}</div>'
        f'  <div class="story-title">{html.escape(title)}</div>'
        f'  <div class="story-body">{sender_info}<br>{body}</div>'
        f'</div>'
    )


def what_happening_panel(state: DashState, focus: str | None,
                         height: int = 500) -> None:
    rows = state.threads.get(focus, []) if focus else state.feed
    title = f"What's happening · {focus}" if focus else "What's happening — all incidents"
    st.markdown(f'<div class="v2-h">{html.escape(title)}</div>',
                unsafe_allow_html=True)
    with st.container(height=height, border=False):
        if not rows:
            st.caption(
                "Press **Start** to run the simulation. "
                "A plain-English log of every decision will appear here."
            )
            return
        items = "".join(_story_row(r) for r in reversed(rows[-300:]))
        st.markdown(
            f'<div class="story-wrap">'
            f'  <div class="story-line"></div>'
            f'  {items}'
            f'</div>',
            unsafe_allow_html=True,
        )


# kept for compat with code that imports `conversation`
def conversation(state: DashState, focus: str | None, height: int = 500) -> None:
    what_happening_panel(state, focus, height)


# ── INCIDENT TABLE ────────────────────────────────────────────────────────────

def incident_table(state: DashState, focus: str | None) -> None:
    st.markdown('<div class="v2-h">Active incidents</div>', unsafe_allow_html=True)
    if not state.incidents:
        st.caption("No calls yet. Press **Start** — each 911 call appears here.")
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
            f'<tr class="{cls}">'
            f'<td class="cad-stripe" style="background:{SEVERITY_COLOR[worst]}"></td>'
            f'<td><b>{inc["id"]}</b><div class="cad-sub">{kind} · {inc["grid"]}</div></td>'
            f'<td>{_triage_chips(inc["triage"])}<div class="cad-sub">waiting / total</div></td>'
            f'<td class="cad-mono">{_units_short(inc["units"])}</td>'
            f'<td>{_pill(inc["status"], STATUS_COLOR.get(inc["status"], "#5B6672"))}</td>'
            f'<td class="cad-mono">{inc["elapsed"]}m</td>'
            f'</tr>'
        )
    st.markdown(
        _scroll(
            '<table class="cad-table"><tr><th></th><th>Incident</th><th>Patients</th>'
            '<th>Units</th><th>Status</th><th>Age</th></tr>'
            + "".join(body) + "</table>"
        ),
        unsafe_allow_html=True,
    )


# ── HOSPITAL CARDS ────────────────────────────────────────────────────────────

def _hospital_type_label(h: dict) -> str:
    caps = set(h.get("capabilities", []))
    if h.get("owner") == "PRIVATE":
        return "Private hospital · surge contract"
    if h.get("stabilization_only"):
        return "Community hospital · stabilization bay (not full trauma)"
    if "TRAUMA_L1" in caps:
        return "Level 1 trauma center · full surgical capability"
    if "TRAUMA_L2" in caps:
        return "Level 2 trauma center · most trauma capable"
    return "Community hospital · general emergency care"


def _res_row(label: str, free: int, total: int) -> str:
    if not total:
        return ""
    frac = (total - free) / total if total else 0
    color = "#FF4757" if free <= 0 else "#FFA502" if frac >= 0.8 else "#2ED573"
    pct = min(100, round(frac * 100))
    return (
        f'<div class="res-row">'
        f'  <div class="res-name">{html.escape(label)}</div>'
        f'  <div class="res-track"><div class="res-fill" style="width:{pct}%;background:{color}"></div></div>'
        f'  <div class="res-num">{free}<span class="cad-sub">/{total}</span></div>'
        f'</div>'
    )


def hospital_board(state: DashState, compact: bool = False) -> None:
    st.markdown('<div class="v2-h">Hospital status</div>', unsafe_allow_html=True)
    if not state.hospitals:
        st.caption("Hospital data will appear once the simulation starts.")
        return
    cards = []
    for hid, h in sorted(state.hospitals.items()):
        status = h.get("status", "OPEN")
        accent = HOSPITAL_STATUS_COLOR.get(status, "#3DD68C")
        pill_bg = {"OPEN": "#2ED573", "BUSY": "#FFA502", "SATURATED": "#FF4757"}.get(status, "#3DD68C")
        pill_label = {"OPEN": "Open", "BUSY": "Busy", "SATURATED": "Full"}.get(status, status)

        occ = h.get("occupied", {})
        tot = h.get("totals", {})

        def fr(r: str, tot=tot, occ=occ) -> tuple[int, int]:
            t = tot.get(r, 0)
            return max(0, t - occ.get(r, 0)), t

        er_f, er_t = fr("er_bed")
        wd_f, wd_t = fr("ward_bed")
        tb_f, tb_t = fr("trauma_bay")
        su_f, su_t = fr("surgeon")

        caps = set(h.get("capabilities", []))
        cap_chips = ""
        if "TRAUMA_L1" in caps or "TRAUMA_L2" in caps:
            cap_chips += '<span class="hosp-cap">🔪 Trauma surgery</span>'
        if h.get("stabilization_only"):
            cap_chips += '<span class="hosp-cap">⚡ Stabilization only</span>'
        if h.get("owner") == "PRIVATE":
            cap_chips += '<span class="hosp-cap">🏦 Private (surge contract)</span>'

        nurses = tot.get("nurse_slot", 0) // 4
        loan_in = h.get("nurses_loaned_in", 0)
        loan_out = h.get("nurses_loaned_out", 0)
        nurse_txt = f"{nurses} nurses"
        if loan_in:
            nurse_txt += f" <b style='color:#3DD68C'>+{loan_in} borrowed</b>"
        if loan_out:
            nurse_txt += f" <b style='color:#FFA502'>−{loan_out} lent out</b>"

        cards.append(
            f'<div class="hosp-card">'
            f'  <div class="hosp-top" style="--ha:{accent}"></div>'
            f'  <div style="display:flex;align-items:flex-start;justify-content:space-between">'
            f'    <div class="hosp-name">{html.escape(h.get("name", "Hospital " + hid))}</div>'
            f'    <span class="hosp-pill" style="background:{pill_bg};color:#07111e">{pill_label}</span>'
            f'  </div>'
            f'  <div class="hosp-type">{html.escape(_hospital_type_label(h))}</div>'
            f'  <div>{cap_chips}</div>'
            + _res_row("ER beds", er_f, er_t)
            + ("" if compact else _res_row("Ward beds", wd_f, wd_t)
               + _res_row("Trauma bays", tb_f, tb_t)
               + _res_row("Surgical teams", su_f, su_t))
            + f'<div class="hosp-footer">'
            f'  <span>👩‍⚕️ {nurse_txt}</span>'
            f'  <span>📥 <b>{h.get("incoming", 0)}</b> incoming</span>'
            f'  <span>🚑 <b>{h.get("ambulances_waiting", 0)}</b> at door</span>'
            f'  <span>⏳ <b>{h.get("queue_scenario", 0)}</b> waiting</span>'
            f'</div>'
            f'</div>'
        )
    st.markdown(
        f'<div class="hosp-grid {"compact" if compact else ""}">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


# ── AMBULANCE UNIT CARDS ──────────────────────────────────────────────────────

def unit_board(state: DashState) -> None:
    st.markdown('<div class="v2-h">Ambulances</div>', unsafe_allow_html=True)
    cards = []
    for u in sorted(state.units.values(), key=lambda u: u["id"]):
        if not u.get("activated"):
            cards.append(
                f'<div class="unit-card" style="opacity:.45">'
                f'  <div class="unit-id">{u["id"]}</div>'
                f'  <div class="unit-state-pill" style="background:rgba(91,102,114,.3);color:#5B6672">'
                f'Standby — private</div>'
                f'  <div class="unit-dest">Activated via mutual aid only</div>'
                f'</div>'
            )
            continue
        state_str = u.get("state", "IDLE")
        color = UNIT_COLOR.get(state_str, "#5B6672")
        label = UNIT_LABEL.get(state_str, state_str)
        dest_parts = []
        if u.get("incident_id"):
            dest_parts.append(f'Scene: {u["incident_id"]}')
        if u.get("hospital_id"):
            dest_parts.append(f'→ Hospital {u["hospital_id"]}')
        dest = " · ".join(dest_parts) if dest_parts else "Waiting for assignment"
        mins = u.get("minutes_in_status", 0)
        cards.append(
            f'<div class="unit-card" style="--ua:{color}">'
            f'  <div class="unit-id">{u["id"]}</div>'
            f'  <div class="unit-state-pill" style="background:{color}22;color:{color};border:1px solid {color}44">'
            f'    {html.escape(label)}'
            f'  </div>'
            f'  <div class="unit-dest">{html.escape(dest)}</div>'
            f'  <div style="font-size:.62rem;color:#3A4A5A;margin-top:.12rem">{mins} min in status</div>'
            f'</div>'
        )
    st.markdown(
        f'<div class="unit-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


# ── AI DECISIONS PANEL ────────────────────────────────────────────────────────

def _neg_pill(msg_type: str) -> str:
    cls = {
        "ACCEPT": "np-accept", "REJECT": "np-reject",
        "COUNTER": "np-counter", "PROPOSE": "np-propose",
        "RESOLVE": "np-resolve", "ESCALATE": "np-escalate",
    }.get(msg_type, "np-propose")
    labels = {
        "ACCEPT": "✅ Accepted", "REJECT": "❌ Rejected",
        "COUNTER": "🔄 Counter-offer", "PROPOSE": "📤 Proposed",
        "RESOLVE": "✅ Resolved", "ESCALATE": "⏸ Escalated",
    }
    return (f'<span class="neg-pill {cls}">'
            f'{html.escape(labels.get(msg_type, msg_type))}</span>')


def _conf_bar(confidence: float | None) -> str:
    if confidence is None:
        return ""
    pct = round(confidence * 100)
    color = "#2ED573" if confidence >= 0.90 else "#FFA502" if confidence >= 0.75 else "#FF4757"
    action = ("Executed automatically" if confidence >= 0.90
              else "Extra info round triggered" if confidence >= 0.75
              else "Sent for human review")
    action_bg = ("#2ED57322" if confidence >= 0.90
                 else "#FFA50222" if confidence >= 0.75
                 else "#FF475722")
    action_col = "#2ED573" if confidence >= 0.90 else "#FFA502" if confidence >= 0.75 else "#FF4757"
    return (
        f'<div class="conf-row">'
        f'  <span style="min-width:4.5rem">AI confidence</span>'
        f'  <div class="conf-track">'
        f'    <div class="conf-fill" style="width:{pct}%;background:{color}"></div>'
        f'  </div>'
        f'  <span class="conf-val" style="color:{color}">{pct}%</span>'
        f'  <span class="conf-action" style="background:{action_bg};color:{action_col}">'
        f'    {html.escape(action)}'
        f'  </span>'
        f'</div>'
    )


def ai_decisions_panel(state: DashState, limit: int = 30) -> None:
    st.markdown('<div class="v2-h">🧠 AI decision log</div>', unsafe_allow_html=True)
    if not state.agent_decisions:
        st.info("No agent calls in this run yet. Choose an agent policy and advance the "
                "simulation to see its activity. Rule policies do not make model calls.")
        return

    recent = state.agent_decisions[-limit:][::-1]
    parts = []
    for d in recent:
        kind = d["agent_kind"]
        color = AGENT_COLOR.get(kind, "#5B6672")
        badge_label = kind.upper()
        desc = d.get("explanation") or AGENT_PLAIN.get(kind, f"Agent: {kind}")
        source_label = ("SCRIPTED" if d.get("source") == "standin"
                        else "CACHED" if d["cache_hit"] else "MODEL CALL")
        cache_span = f'<span class="cache-hit">{source_label}</span>'
        toks = f'{d.get("tokens", 0):,} tokens' if d.get("tokens") else ""
        lat = f' · {d["latency_ms"]:.0f} ms' if d.get("latency_ms") else ""
        inc_tag = (f' · {d["incident_id"]}' if d.get("incident_id") else "")
        parts.append(
            f'<div class="ai-card" style="--aa:{color}">'
            f'  <div class="ai-header">'
            f'    <span class="ai-badge" style="background:{color}22;color:{color};border:1px solid {color}44">'
            f'      {html.escape(badge_label)}'
            f'    </span>'
            f'    {cache_span}'
            f'    <span class="ai-toks">{html.escape(toks + lat + inc_tag)}</span>'
            f'    <span class="ai-time">{d["wall"]}</span>'
            f'  </div>'
            f'  <div class="ai-desc">{html.escape(desc)}</div>'
            + _conf_bar(d.get("confidence"))
            + '</div>'
        )
    st.markdown("".join(parts), unsafe_allow_html=True)

    # negotiation summary
    if state.negotiations:
        st.markdown('<div class="v2-h" style="margin-top:.8rem">Hospital negotiations</div>',
                    unsafe_allow_html=True)
        neg_html = []
        for n in state.negotiations[-40:][::-1]:
            neg_html.append(
                f'<div style="font-size:.72rem;color:#5A6A7A;margin-bottom:.1rem">'
                f'  <span style="font-family:\'JetBrains Mono\',monospace">{n["wall"]}</span>'
                f'  {_neg_pill(n["msg_type"])}'
                f'  <span style="color:#9AB0C0">{html.escape(n.get("reason", "")[:80])}</span>'
                f'</div>'
            )
        st.markdown("".join(neg_html), unsafe_allow_html=True)


# ── MCI BOARD ────────────────────────────────────────────────────────────────

def mci_board(state: DashState) -> None:
    mcis = [i for i in state.incidents.values() if i["victims"] > 3]
    if not mcis:
        st.caption("No mass-casualty incident in this scenario.")
        return
    for inc in mcis:
        kind = inc["type"].replace("_", " ").title()
        st.markdown(
            f'<div class="v2-h">{inc["id"]} · {kind} · {inc["victims"]} victims '
            f'(caller reported {inc["reported"]})</div>',
            unsafe_allow_html=True,
        )
        left, right = st.columns(2, gap="large")
        rows = "".join(
            f'<tr>'
            f'<td><span class="cad-tri" style="background:{TRIAGE_COLOR[c]}">{c}</span></td>'
            f'<td class="cad-mono">{v["total"]}</td>'
            f'<td class="cad-mono">{v["on_scene"]}</td>'
            f'<td class="cad-mono">{v["transport"]}</td>'
            f'<td class="cad-mono">{v["hospital"]}</td>'
            f'<td class="cad-mono">{v["died"]}</td>'
            f'</tr>'
            for c, v in inc["triage"].items() if v["total"]
        )
        left.markdown(
            '<table class="cad-table"><tr>'
            '<th>Triage</th><th>Total</th><th>On scene</th>'
            '<th>In transport</th><th>At hospital</th><th>Died</th>'
            f'</tr>{rows}</table>',
            unsafe_allow_html=True,
        )
        summary = transport_summary(state, inc["id"])
        if summary:
            rows2 = "".join(
                f'<tr><td><b>Hospital {hid}</b></td>'
                + "".join(f'<td class="cad-mono">{counts[c]}</td>'
                          for c in TRIAGE.values())
                + f'<td class="cad-mono">{sum(counts.values())}</td></tr>'
                for hid, counts in summary.items()
            )
            right.markdown(
                '<table class="cad-table"><tr>'
                '<th>Sent to</th><th>Red</th><th>Yellow</th><th>Green</th>'
                f'<th>Black</th><th>Total</th></tr>{rows2}</table>',
                unsafe_allow_html=True,
            )
        else:
            right.caption("No patients have reached a hospital yet.")


# ── TIMELINE / METRICS ───────────────────────────────────────────────────────

def timeline(state: DashState, events, timings, focus: str | None) -> None:
    if not state.handling:
        st.caption("Handling time data appears once calls arrive.")
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
        "incident_id", "type", "call_tick", "victims",
        "decision_min", "scene_min", "hospital_min",
        "care_mean_min", "care_max_min", "in_care", "deceased", "rejections",
    ]]
    df.columns = [
        "Incident", "Type", "Called (min)", "Victims",
        "→ dispatch", "→ scene", "→ hospital",
        "→ care avg", "→ care max", "In care", "Died", "Blocked",
    ]
    st.dataframe(df, hide_index=True, use_container_width=True)
    sev = pd.DataFrame(by_severity(patient_handling(events)))
    if not sev.empty:
        st.markdown("**Time from call to treatment, by severity (simulated minutes)**")
        st.dataframe(sev, hide_index=True, use_container_width=True)
    d = decision_time(timings, events)
    st.caption(
        f"Engine made {d['decisions']} decisions in {d['total_ms']:.0f} ms total "
        f"({d['mean_ms_per_decision']:.2f} ms each). "
        f"AI calls: {d['llm_calls']}, tokens used: {d['tokens']}."
    )


# ── MAP SIDEBAR (compat) ──────────────────────────────────────────────────────

LEGEND = [
    ("border-radius:50%", "#3DD68C", "Hospital (green=open, orange=busy, red=full)"),
    ("border-radius:50%", "#FF4757", "Emergency call (bigger = more victims)"),
    ("transform:rotate(45deg)", "#FFA502", "Ambulance station"),
    ("clip-path:polygon(50% 0,100% 100%,0 100%)", "#4C9EFF", "Ambulance (colour = status)"),
    ("height:.12rem;border-radius:0", "#4C9EFF", "Route: going to call"),
    ("height:.12rem;border-radius:0", "#FF4757", "Route: transporting to hospital"),
]


def map_sidebar(state: DashState, town_population: int, area_km: float) -> set[str]:
    from app.map_view import LAYERS

    units = [u for u in state.units.values() if u.get("activated")]
    homes = {tuple(u["home"]) for u in units if u.get("home")}
    tiles = [
        (f"{town_population:,}", "residents"),
        (len(state.hospitals), "hospitals"),
        (len(units), "ambulances on duty"),
        (len(homes), "stations"),
        (f"{area_km * area_km:.0f}", "km² town area"),
        (state.kpis["active_calls"], "active calls"),
    ]
    st.markdown(
        '<div class="side-tiles">'
        + "".join(
            f'<div class="side-tile"><b>{v}</b><span>{html.escape(str(label))}</span></div>'
            for v, label in tiles
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="cad-h">Map layers</div>', unsafe_allow_html=True)
    layers = {name for name in LAYERS if st.toggle(name, value=True, key=f"v2_layer_{name}")}
    st.markdown(
        '<div class="v2-h" style="margin-top:.6rem">Legend</div>'
        + "".join(
            f'<div class="legend-row">'
            f'<i style="background:{c};{shape}"></i>{html.escape(t)}</div>'
            for shape, c, t in LEGEND
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="v2-h" style="margin-top:.7rem">Hospitals</div>'
        + "".join(
            f'<div class="side-h"><span><b>{hid}</b></span>'
            f'{_pill(h.get("status","?"), HOSPITAL_STATUS_COLOR.get(h.get("status","OPEN"),"#3DD68C"))}'
            f'</div>'
            for hid, h in sorted(state.hospitals.items())
        ),
        unsafe_allow_html=True,
    )
    return layers
