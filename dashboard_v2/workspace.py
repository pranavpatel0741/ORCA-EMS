"""Purpose-built views for the v2 operations workspace."""

from __future__ import annotations

import html
from collections import Counter

import streamlit as st

from dashboard_v2.state import DashState, wall_clock

SOURCE = {
    "ai": "AI agent",
    "standin": "Scripted agent",
    "rules": "Rule policy",
    "backup": "Rule backup",
    "sim": "Simulation",
}
COLORS = {"RED": "#d85440", "YELLOW": "#c28a25", "GREEN": "#21866d", "BLACK": "#778292"}


def markup(value: str) -> None:
    st.markdown(value, unsafe_allow_html=True)


def heading(title: str, detail: str = "", tag: str = "") -> None:
    markup(
        f'<div class="section-heading"><div><h3>{html.escape(title)}</h3>'
        f"<p>{html.escape(detail)}</p></div><span>{html.escape(tag)}</span></div>"
    )


def overview_metrics(state: DashState) -> None:
    k = state.kpis
    critical = sum(
        p["severity"] == "CRITICAL"
        and p["status"] in ("WAITING_ON_SCENE", "IN_TRANSPORT", "WAITING_AT_ER")
        for p in state.patients.values()
        if p["incident_id"] in state.incidents
    )
    tiles = [
        ("Open incidents", str(k["active_calls"]), f"{k['calls']} calls received", "orange"),
        (
            "Available ambulances",
            f"{k['free_units']}<small> / {k['units']}</small>",
            f"{k['units'] - k['free_units']} responding or returning",
            "blue",
        ),
        (
            "Critical awaiting care",
            str(critical),
            f"{k['waiting_at_er']} patients waiting at ER",
            "red",
        ),
        ("Patients reached care", str(k["in_care"]), f"{k['deceased']} deaths recorded", "green"),
    ]
    markup(
        '<div class="overview-metrics">'
        + "".join(
            f'<div class="overview-metric {color}"><div class="metric-eyebrow">{label}</div>'
            f'<div class="metric-number">{value}</div>'
            f'<div class="metric-detail">{detail}</div></div>'
            for label, value, detail, color in tiles
        )
        + "</div>"
    )


def hospital_grid(state: DashState, detailed: bool = False) -> None:
    cards = []
    for hid, h in sorted(state.hospitals.items()):
        occupied, total = h["occupied"], h["totals"]
        status = h.get("status", "OPEN")
        css = {"OPEN": "green", "BUSY": "amber", "SATURATED": "red"}.get(status, "green")
        status_label = {"OPEN": "Accepting", "BUSY": "Busy", "SATURATED": "At capacity"}[status]
        caps = set(h.get("capabilities", []))
        kind = (
            "Trauma center"
            if caps & {"TRAUMA_L1", "TRAUMA_L2"}
            else "Stabilization only"
            if h.get("stabilization_only")
            else "General emergency"
        )
        if h.get("owner") == "PRIVATE":
            kind += " · Private"
        rows = []
        resources = [("er_bed", "Emergency beds")]
        if detailed:
            resources += [
                ("ward_bed", "Ward beds"),
                ("trauma_bay", "Trauma bays"),
                ("surgeon", "Surgical teams"),
            ]
        for resource, label in resources:
            capacity = total.get(resource, 0)
            if not capacity:
                continue
            used = occupied.get(resource, 0)
            free = max(0, capacity - used)
            percent = min(100, max(0, used / capacity * 100))
            rows.append(
                f'<div class="capacity-label"><span>{label}</span><b>{free}'
                f"<small> / {capacity} free</small></b></div>"
                f'<div class="capacity-track"><i class="{css}" '
                f'style="width:{percent:.1f}%"></i></div>'
            )
        cards.append(
            f'<article class="network-card"><div class="network-top"><div class="hospital-icon">'
            f'{html.escape(hid)}</div><span class="status-tag {css}">{status_label}</span></div>'
            f"<h4>{html.escape(h.get('name', 'Hospital ' + hid))}</h4>"
            f'<p>{kind}</p>{"".join(rows)}<div class="network-footer">'
            f"<span><b>{h.get('incoming', 0)}</b> incoming</span>"
            f"<span><b>{h.get('queue_scenario', 0)}</b> waiting</span></div></article>"
        )
    markup('<div class="network-grid">' + "".join(cards) + "</div>")


def incident_inspector(state: DashState, focus: str | None) -> None:
    if not state.incidents:
        markup(
            '<div class="empty-incident"><div class="empty-symbol">◎</div>'
            "<h4>Ready for the first call</h4><p>Start the scenario or advance 15 minutes "
            "to follow a response from call to care.</p>"
            "<span>Every call, assignment, and handover comes from the simulation.</span></div>"
        )
        return
    if not focus:
        active = sorted(
            state.incidents.values(),
            key=lambda i: (i["status"] == "CLEARED", -i["waiting"], i["call_tick"]),
        )
        for inc in active[:5]:
            label = inc["type"].replace("_", " ").title()
            markup(
                f'<div class="queue-card"><div class="queue-top"><b>{html.escape(inc["id"])}'
                f'</b><span class="queue-age">+{inc["elapsed"]} min</span></div>'
                f'<h4>{html.escape(label)}</h4><div class="queue-bottom">'
                f"<span>{inc['waiting']} waiting / {inc['victims']} patients</span>"
                f'<span class="queue-status">{inc["status"].title()}</span></div></div>'
            )
        if len(active) > 5:
            st.caption(f"Showing 5 of {len(active)} incidents. Select an incident to inspect it.")
        return
    inc = state.incidents[focus]
    markup(
        f'<div class="incident-heading"><span class="case-id">{html.escape(focus)}</span>'
        f"<h3>{html.escape(inc['type'].replace('_', ' ').title())}</h3>"
        f"<p>{html.escape(inc['grid'])} · Received {wall_clock(inc['call_tick'])}</p>"
        f'<span class="status-tag blue">{inc["status"].title()}</span></div>'
    )
    markup(
        '<div class="triage-summary">'
        + "".join(
            f'<div><i style="background:{COLORS[color]}"></i><b>{counts["total"]}</b>'
            f"<span>{color.title()}</span></div>"
            for color, counts in inc["triage"].items()
        )
        + "</div>"
    )
    st.caption(inc.get("narrative", ""))
    handling = next((r for r in state.handling if r["incident_id"] == focus), {})
    journey = [
        ("Call received", 0),
        ("Unit dispatched", handling.get("decision_min")),
        ("On scene", handling.get("scene_min")),
        ("At hospital", handling.get("hospital_min")),
        ("Treatment started · avg", handling.get("care_mean_min")),
    ]
    markup(
        '<div class="care-journey">'
        + "".join(
            f'<div class="journey-step {"complete" if value is not None else ""}">'
            f"<i></i><span>{label}</span><b>{f'+{value:g}m' if value is not None else 'Pending'}"
            f"</b></div>"
            for label, value in journey
        )
        + "</div>"
    )
    units = ", ".join(inc.get("units", [])) or "No units currently assigned"
    markup(f'<div class="assignment-note">Assigned units<b>{html.escape(units)}</b></div>')


def fleet_strip(state: DashState) -> None:
    units = [u for u in state.units.values() if u.get("activated")]
    markup(
        '<div class="fleet-strip"><span class="fleet-label">ON DUTY</span>'
        + "".join(
            f'<span class="fleet-unit">'
            f'<i class="{"available" if u["state"] == "IDLE" else ""}"></i>'
            f"<b>{html.escape(u['id'])}</b>"
            f"<small>{u['state'].replace('_', ' ').title()}</small></span>"
            for u in units
        )
        + "</div>"
    )


def activity(state: DashState, focus: str | None = None, limit: int = 5) -> None:
    rows = state.threads.get(focus, []) if focus else state.feed
    if not rows:
        markup(
            '<div class="quiet-state">The decision trail will appear as the response unfolds.</div>'
        )
        return
    parts = []
    for row in reversed(rows[-limit:]):
        parts.append(
            f'<div class="activity-entry"><div class="activity-time">{wall_clock(row.tick)}</div>'
            f'<div class="activity-main"><div class="activity-title">{html.escape(row.sender)}'
            f"<span> → {html.escape(row.recipient)}</span>"
            f"<em>{SOURCE.get(row.source, 'Simulation')}</em></div>"
            f"<p>{html.escape(row.text)}</p></div></div>"
        )
    markup('<div class="activity-list">' + "".join(parts) + "</div>")


def agent_pipeline(state: DashState) -> None:
    counts = Counter(d["agent_kind"] for d in state.agent_decisions)
    stages = [
        ("01", "Assessment", "assessment", "Understand the emergency"),
        ("02", "Dispatch", "dispatch", "Assign the response"),
        ("03", "Hospital agents", "hospital", "Negotiate available care"),
        ("04", "Allocator", "allocator", "Resolve disagreements"),
    ]
    markup(
        '<div class="agent-pipeline">'
        + "".join(
            f'<div class="agent-stage"><span>{n}</span><h4>{title}</h4><p>{desc}</p>'
            f"<b>{counts[kind]} calls recorded</b></div>"
            for n, title, kind, desc in stages
        )
        + "</div>"
    )


def incident_register(state: DashState) -> None:
    columns = ["Incident", "Emergency", "Patients", "Waiting", "Assigned units", "Status"]
    rows = [
        [
            i["id"],
            i["type"].replace("_", " ").title(),
            i["victims"],
            i["waiting"],
            ", ".join(i["units"]) or "—",
            i["status"].title(),
        ]
        for i in state.incidents.values()
    ]
    table(columns, rows)


def table(columns: list[str], rows: list[list]) -> None:
    if not rows:
        markup(
            '<div class="quiet-state">No records yet. Advance the simulation to collect data.</div>'
        )
        return
    markup(
        '<div class="report-scroll"><table class="report-table"><thead><tr>'
        + "".join(f"<th>{html.escape(str(c))}</th>" for c in columns)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def fleet_board(state: DashState, filter_by: str = "All units") -> None:
    units = list(state.units.values())
    if filter_by == "Available":
        units = [u for u in units if u.get("activated") and u["state"] == "IDLE"]
    elif filter_by == "Responding":
        units = [u for u in units if u.get("activated") and u["state"] != "IDLE"]
    elif filter_by == "Standby":
        units = [u for u in units if not u.get("activated")]
    if not units:
        markup(
            '<div class="quiet-state">No units match this filter. '
            "Choose All units to see the fleet.</div>"
        )
        return
    table(
        ["Unit", "Status", "Scene", "Destination", "Time in status"],
        [
            [
                u["id"],
                u["state"].replace("_", " ").title() if u.get("activated") else "Private standby",
                u.get("incident_id") or "—",
                u.get("hospital_id") or "—",
                f"{u.get('minutes_in_status', 0)} min",
            ]
            for u in units
        ],
    )


def report(state: DashState) -> None:
    import plotly.graph_objects as go

    overview_metrics(state)
    heading("Time from call to care", "Simulated minutes · lower is faster")
    if not state.handling:
        markup('<div class="quiet-state">Response timings appear after the first call.</div>')
        return
    fig = go.Figure()
    for key, label, color in [
        ("decision_min", "Dispatched", "#91b3de"),
        ("scene_min", "On scene", "#506d96"),
        ("care_mean_min", "Treatment started · avg", "#ed925e"),
    ]:
        fig.add_trace(
            go.Bar(
                y=[r["incident_id"] for r in state.handling],
                x=[r.get(key) for r in state.handling],
                name=label,
                orientation="h",
                marker_color=color,
                hovertemplate="%{y}<br>%{x} simulated min<extra>" + label + "</extra>",
            )
        )
    fig.update_layout(
        height=max(280, min(650, len(state.handling) * 60 + 100)),
        barmode="group",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#6b8098", size=11),
        margin=dict(l=10, r=10, t=15, b=10),
        legend=dict(orientation="h", y=-0.2),
        xaxis=dict(gridcolor="#edf1f5", title="Minutes since call"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(
        "Missing timings mean the milestone has not been reached. Average treatment time "
        "includes only patients who reached care; deaths are listed separately."
    )
    table(
        ["Incident", "Dispatch", "On scene", "Hospital", "Care · avg", "In care", "Deaths"],
        [
            [
                r["incident_id"],
                *[
                    "Pending" if r.get(k) is None else f"{r[k]:g} min"
                    for k in ("decision_min", "scene_min", "hospital_min", "care_mean_min")
                ],
                f"{r['in_care']}/{r['victims']}",
                r["deceased"],
            ]
            for r in state.handling
        ],
    )
