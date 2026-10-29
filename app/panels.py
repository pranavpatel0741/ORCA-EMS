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


def clock_html(tick: int) -> str:
    return f'<div class="cad-clock">{wall_clock(tick)}<small>MINUTE {tick}</small></div>'


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


def _message(r: FeedRow) -> str:
    label, color = ROLE.get(r.role, ROLE["system"])
    if r.role == "hospital" and r.sender.startswith("Hospital "):
        label = "H-" + r.sender.split()[-1]
    cls = "reject" if r.category == "reject" else "flag" if r.category == "flag" else ""
    tag_color = {"reject": "#E5484D", "flag": "#F2A33A"}.get(r.category, "#7D8A97")
    return (f'<div class="msg {cls}"><div class="av" style="background:{color}">{label}</div>'
            f'<div><div class="hd"><b>{html.escape(r.sender)}</b><span>→ '
            f'{html.escape(r.recipient)}</span><span class="tag" style="color:{tag_color}">'
            f'{html.escape(r.kind)}</span><span class="t">{wall_clock(r.tick)}</span></div>'
            f'<div class="tx">{html.escape(r.text)}</div></div></div>')


def conversation(state: DashState, focus: str | None, height: int = 600) -> None:
    rows = state.threads.get(focus, []) if focus else state.feed
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
