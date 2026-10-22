"""Streamlit panels: KPI bar, hospital capacity cards, call threads, message feed, tables."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from app.state import DashState, FeedRow
from eval.handling import by_severity, decision_time, patient_handling

CATEGORY_COLOR = {
    "call": "#4C9EFF", "agent": "#B18CFF", "decision": "#3DD68C", "reject": "#E5484D",
    "flag": "#F2A33A", "unit": "#7D8A97", "hospital": "#2EC4B6", "patient": "#C9D3DD",
    "alert": "#F2A33A",
}
CSS = """
<style>
.orca-row{display:grid;grid-template-columns:3.4rem 11rem 9rem 1fr;gap:.6rem;
  padding:.28rem .2rem;border-bottom:1px solid rgba(140,160,180,.12);font-size:.86rem;
  align-items:baseline}
.orca-t{font-family:ui-monospace,Menlo,monospace;color:#7D8A97;font-size:.8rem}
.orca-who{color:#C9D3DD;font-size:.8rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.orca-kind{font-size:.7rem;font-weight:700;letter-spacing:.04em;padding:.08rem .4rem;
  border-radius:.25rem;border:1px solid currentColor;justify-self:start;white-space:nowrap}
.orca-text{color:#E6EDF3;min-width:0;overflow-wrap:anywhere}
.orca-card{border:1px solid rgba(140,160,180,.22);border-radius:.4rem;padding:.6rem .75rem;
  margin-bottom:.6rem;background:rgba(17,26,35,.55)}
.orca-card h4{margin:0 0 .35rem 0;font-size:.95rem;color:#E6EDF3}
.orca-bar{display:grid;grid-template-columns:6.5rem 1fr 3.6rem;gap:.5rem;align-items:center;
  font-size:.8rem;color:#C9D3DD;margin:.14rem 0}
.orca-track{height:.5rem;background:rgba(140,160,180,.18);border-radius:.25rem;overflow:hidden}
.orca-fill{height:100%;border-radius:.25rem}
.orca-num{font-family:ui-monospace,Menlo,monospace;text-align:right;font-size:.78rem}
.orca-note{font-size:.75rem;color:#7D8A97;margin-top:.3rem}
.orca-strip{display:flex;flex-wrap:wrap;gap:.4rem;margin:.1rem 0 .5rem 0}
.orca-chip{font-size:.75rem;padding:.12rem .5rem;border-radius:1rem;
  background:rgba(140,160,180,.14);color:#C9D3DD;font-family:ui-monospace,Menlo,monospace}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def clock(tick: int) -> str:
    return f"T+{tick}"


def kpi_bar(state: DashState) -> None:
    k = state.kpis
    cols = st.columns(8)
    cols[0].metric("Sim time", f"{state.tick} min")
    cols[1].metric("Calls", k["calls"])
    cols[2].metric("Waiting on scene", k["waiting_on_scene"])
    cols[3].metric("In transport", k["in_transport"])
    cols[4].metric("Waiting at ER", k["waiting_at_er"])
    cols[5].metric("In care", k["in_care"])
    cols[6].metric("Deceased", k["deceased"])
    cols[7].metric("Free ambulances", f"{k['free_units']}/{k['units']}")


def _bar(label: str, used: int, total: int) -> str:
    frac = used / total if total else 0
    color = "#E5484D" if frac >= 1 else "#F2A33A" if frac >= 0.8 else "#3DD68C"
    width = min(100, round(frac * 100))
    return (f'<div class="orca-bar"><span>{label}</span><div class="orca-track">'
            f'<div class="orca-fill" style="width:{width}%;background:{color}"></div></div>'
            f'<span class="orca-num">{used}/{total}</span></div>')


def hospital_cards(state: DashState) -> None:
    for hid, h in sorted(state.hospitals.items()):
        occ, tot = h["occupied"], h["totals"]
        rows = [_bar("ER beds", occ["er_bed"], tot["er_bed"])]
        if tot.get("ward_bed"):
            rows.append(_bar("Ward beds", occ["ward_bed"], tot["ward_bed"]))
        if tot["trauma_bay"]:
            label = "Stab. bay" if h.get("stabilization_only") else "Trauma bays"
            rows.append(_bar(label, occ["trauma_bay"], tot["trauma_bay"]))
        if tot["surgeon"]:
            rows.append(_bar("Surgical teams", occ["surgeon"], tot["surgeon"]))
        if tot["or"]:
            rows.append(_bar("ORs", occ["or"], tot["or"]))
        rows.append(_bar("Nurse slots", occ["nurse_slot"], tot["nurse_slot"]))
        extras = [f"queue {h['queue_scenario']}", f"boarding {h.get('boarding', 0)}",
                  f"ambulances at door {h['ambulances_waiting']}"]
        if h["nurses_loaned_in"] or h["nurses_loaned_out"]:
            extras.append(f"nurses +{h['nurses_loaned_in']}/-{h['nurses_loaned_out']}")
        last = state.hospital_changes.get(hid, [])
        note = html.escape(last[-1]) if last else "no scenario patients yet"
        owner = "private" if h.get("owner") == "PRIVATE" else "public"
        st.markdown(
            f'<div class="orca-card"><h4>{html.escape(h.get("name", hid))} '
            f'<span style="color:#7D8A97;font-weight:400;font-size:.8rem">· {owner}</span></h4>'
            + "".join(rows)
            + f'<div class="orca-note">{" · ".join(extras)}</div>'
            + f'<div class="orca-note">last change: {note}</div></div>',
            unsafe_allow_html=True,
        )


def _row(r: FeedRow) -> str:
    color = CATEGORY_COLOR.get(r.category, "#C9D3DD")
    return (f'<div class="orca-row"><span class="orca-t">{clock(r.tick)}</span>'
            f'<span class="orca-who">{html.escape(r.sender)} → {html.escape(r.recipient)}</span>'
            f'<span class="orca-kind" style="color:{color}">{html.escape(r.kind)}</span>'
            f'<span class="orca-text">{html.escape(r.text)}</span></div>')


def _chips(row: dict) -> str:
    def m(v):
        return "—" if v is None else f"{v} min"
    chips = [f"decision {m(row['decision_min'])}", f"scene {m(row['scene_min'])}",
             f"hospital {m(row['hospital_min'])}",
             f"care avg {m(row['care_mean_min'])} ({row['in_care']}/{row['victims']})"]
    if row["rejections"]:
        chips.append(f"{row['rejections']} rejected")
    if row["deceased"]:
        chips.append(f"{row['deceased']} died")
    return '<div class="orca-strip">' + "".join(
        f'<span class="orca-chip">{html.escape(c)}</span>' for c in chips) + "</div>"


def call_threads(state: DashState) -> None:
    if not state.incidents:
        st.info("No calls yet. Press Play to start the shift; each 911 call opens a thread here.")
        return
    handling = {r["incident_id"]: r for r in state.handling}
    newest_first = sorted(state.incidents.values(), key=lambda i: (-i["call_tick"], i["id"]))
    for i, inc in enumerate(newest_first):
        title = (f"{inc['id']} · {inc['type'].replace('_', ' ').title()} · {inc['victims']} "
                 f"victim(s) · called {clock(inc['call_tick'])} · waiting {inc['waiting']}")
        with st.expander(title, expanded=i < 2 or inc["victims"] > 5):
            st.markdown(_chips(handling[inc["id"]]) if inc["id"] in handling else "",
                        unsafe_allow_html=True)
            st.markdown("".join(_row(r) for r in state.threads.get(inc["id"], [])),
                        unsafe_allow_html=True)


def message_feed(state: DashState) -> None:
    c1, c2 = st.columns([2, 1])
    hidden = c1.multiselect("Hide message types", list(CATEGORY_COLOR), default=[],
                            key="feed_hidden")
    calls = ["all"] + sorted(state.incidents)
    call = c2.selectbox("Call", calls, key="feed_call")
    rows = [r for r in reversed(state.feed) if r.category not in hidden
            and (call == "all" or r.incident_id == call)]
    st.caption(f"{len(rows)} messages, newest first")
    st.markdown("".join(_row(r) for r in rows[:300]), unsafe_allow_html=True)


def handling_tab(state: DashState, events, timings) -> None:
    if not state.handling:
        st.info("Handling times appear once calls arrive.")
        return
    df = pd.DataFrame(state.handling)[[
        "incident_id", "type", "call_tick", "victims", "decision_min", "scene_min",
        "hospital_min", "care_mean_min", "care_max_min", "in_care", "deceased", "rejections",
        "messages"]]
    st.markdown("**Per call** (simulated minutes from the 911 call)")
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.markdown("**By severity**: call to definitive care")
    st.dataframe(pd.DataFrame(by_severity(patient_handling(events))), hide_index=True,
                 use_container_width=True)
    d = decision_time(timings, events)
    st.markdown("**Real decision time** (wall clock; LLM numbers appear once agents run)")
    cols = st.columns(5)
    cols[0].metric("Decisions", d["decisions"])
    cols[1].metric("Total decide time", f"{d['total_ms']:.0f} ms")
    cols[2].metric("Per decision", f"{d['mean_ms_per_decision']:.2f} ms")
    cols[3].metric("LLM calls", d["llm_calls"])
    cols[4].metric("Tokens", d["tokens"])


def units_table(state: DashState) -> None:
    rows = [{"unit": u["id"], "status": u["state"].replace("_", " ").lower(),
             "call": u.get("incident_id") or "", "hospital": u.get("hospital_id") or "",
             "in service": "yes" if u.get("activated") else "standby (mutual aid)"}
            for u in sorted(state.units.values(), key=lambda u: u["id"])]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
