"""A separate cartographic view for the v2 workspace; no external map service."""

from __future__ import annotations

import html

import plotly.graph_objects as go

from dashboard_v2.state import DashState
from sim.town import TownProfile

STATUS = {
    "IDLE": "#14806c",
    "EN_ROUTE": "#3978d5",
    "TRANSPORTING": "#dc683c",
    "STAGING": "#9163ba",
    "WAITING_AT_ER": "#bc8428",
}
SEVERITY = {"CRITICAL": "#d85440", "SERIOUS": "#cf8b28", "MINOR": "#21866d", "EXPECTANT": "#798394"}


def response_map(
    state: DashState, town: TownProfile, focus: str | None, layers: set[str]
) -> go.Figure:
    fig = go.Figure()
    size = town.area_km
    shapes = []
    annotations = []
    # District labels and subtle land parcels give spatial context without implying real GIS.
    districts = [
        (0, 0, "SOUTH WEST"),
        (10, 0, "SOUTH EAST"),
        (0, 10, "NORTH WEST"),
        (10, 10, "NORTH EAST"),
    ]
    for x, y, label in districts:
        shapes.append(
            dict(
                type="rect",
                x0=x + 0.2,
                x1=x + 9.8,
                y0=y + 0.2,
                y1=y + 9.8,
                fillcolor="#e7edf0",
                line=dict(width=0),
                layer="below",
            )
        )
        annotations.append(
            dict(
                x=x + 5, y=y + 8.5, text=label, showarrow=False, font=dict(size=10, color="#9daeb6")
            )
        )
    if "Street grid" in layers:
        for v in range(1, int(size)):
            major = v % 5 == 0
            for vertical in (True, False):
                shapes.append(
                    dict(
                        type="line",
                        x0=v if vertical else 0,
                        x1=v if vertical else size,
                        y0=0 if vertical else v,
                        y1=size if vertical else v,
                        line=dict(
                            color="#ffffff" if major else "#f4f7f8", width=5 if major else 1.7
                        ),
                        layer="below",
                    )
                )
        shapes.append(
            dict(
                type="path",
                path="M 0,3 L 4,6 L 8,10 L 14,13 L 20,18",
                line=dict(color="#d4dde2", width=9),
                layer="below",
            )
        )
        shapes.append(
            dict(
                type="path",
                path="M 0,3 L 4,6 L 8,10 L 14,13 L 20,18",
                line=dict(color="#ffffff", width=4),
                layer="below",
            )
        )
    shapes.append(
        dict(
            type="rect",
            x0=0,
            x1=size,
            y0=0,
            y1=size,
            line=dict(color="#c7d3db", width=1, dash="dot"),
            layer="below",
        )
    )
    if "Stations" in layers:
        homes = sorted(
            {tuple(u["home"]) for u in state.units.values() if u.get("home") and u.get("activated")}
        )
        points = [town.to_km(*p) for p in homes]
        if points:
            fig.add_trace(
                go.Scatter(
                    x=[p[0] for p in points],
                    y=[p[1] for p in points],
                    mode="markers",
                    name="Station",
                    marker=dict(
                        symbol="square", size=10, color="#8997a8", line=dict(color="white", width=2)
                    ),
                    hovertemplate="Ambulance station<extra></extra>",
                )
            )
    if "Routes" in layers:
        for unit in state.units.values():
            incident = state.incidents.get(unit.get("incident_id"))
            hospital = state.hospitals.get(unit.get("hospital_id"))
            if not incident:
                continue
            if unit["state"] == "EN_ROUTE" and unit.get("home"):
                a, b = unit["home"], incident["location"]
            elif unit["state"] == "TRANSPORTING" and hospital:
                a, b = incident["location"], hospital["location"]
            else:
                continue
            a, b = town.to_km(*a), town.to_km(*b)
            color = STATUS.get(unit["state"], "#3978d5")
            fig.add_trace(
                go.Scatter(
                    x=[a[0], b[0]],
                    y=[a[1], b[1]],
                    mode="lines",
                    name="Assignment",
                    line=dict(color=color, width=3, dash="dot"),
                    hoverinfo="skip",
                    opacity=0.8,
                )
            )
    for hid, hospital in sorted(state.hospitals.items()):
        x, y = town.to_km(*hospital["location"])
        status = hospital.get("status", "OPEN")
        color = {"OPEN": "#14806c", "BUSY": "#bc8428", "SATURATED": "#d85440"}[status]
        free = hospital["totals"]["er_bed"] - hospital["occupied"]["er_bed"]
        label = html.escape(hospital.get("name", hid))
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers+text",
                name=f"Hospital {hid}",
                marker=dict(
                    symbol="square", size=30, color="white", line=dict(color=color, width=2)
                ),
                text=["H"],
                textfont=dict(size=17, color=color),
                textposition="middle center",
                hovertemplate=f"<b>{label}</b><br>{status.title()} · {free} ER beds free"
                f"<br>{hospital.get('incoming', 0)} incoming<extra></extra>",
            )
        )
        if "Labels" in layers:
            annotations.append(
                dict(
                    x=x,
                    y=y - 1.1,
                    text=f"<b>{label}</b>",
                    showarrow=False,
                    font=dict(size=10, color="#46566d"),
                    bgcolor="#f7f9fb",
                    borderpad=3,
                )
            )
    for number, incident in enumerate(state.incidents.values(), 1):
        x, y = town.to_km(*incident["location"])
        worst = next((s for s in SEVERITY if s in incident["severities"]), "MINOR")
        color = SEVERITY[worst] if incident["status"] != "CLEARED" else "#8997a8"
        if incident["waiting"] or incident["id"] == focus:
            fig.add_trace(
                go.Scatter(
                    x=[x],
                    y=[y],
                    mode="markers",
                    hoverinfo="skip",
                    marker=dict(size=52, color=color, opacity=0.13),
                )
            )
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers+text",
                name=incident["id"],
                customdata=[incident["id"]],
                marker=dict(size=29, color=color, line=dict(color="white", width=2)),
                text=[str(number)],
                textposition="middle center",
                textfont=dict(size=12, color="white"),
                hovertemplate=f"<b>{html.escape(incident['id'])}</b><br>"
                f"{html.escape(incident['type'].replace('_', ' ').title())}"
                f"<br>{incident['waiting']} waiting · {incident['victims']} patients"
                f"<br>{incident['status']}<extra></extra>",
            )
        )
    positions = {}
    for uid, unit in sorted(state.units.items()):
        if not unit.get("activated") or not unit.get("location"):
            continue
        x, y = town.to_km(*unit["location"])
        n = positions.get((x, y), 0)
        positions[x, y] = n + 1
        x, y = x + 0.75 + n % 3 * 0.55, y + 0.65 + n // 3 * 0.55
        color = STATUS.get(unit["state"], "#9163ba")
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers",
                name=uid,
                marker=dict(
                    symbol="diamond", size=11, color=color, line=dict(color="white", width=1.5)
                ),
                hovertemplate=f"<b>{uid}</b><br>{unit['state'].replace('_', ' ').title()}"
                "<extra></extra>",
            )
        )
    annotations.extend(
        [
            dict(x=19.4, y=20.8, text="N ↑", showarrow=False, font=dict(size=12, color="#52647a")),
            dict(
                x=0.2,
                y=-1,
                text="0 ━━━ 5 km",
                showarrow=False,
                xanchor="left",
                font=dict(size=10, color="#7c8c9e"),
            ),
        ]
    )
    axis = dict(
        showgrid=False, zeroline=False, visible=False, fixedrange=True, range=[-1.8, size + 1.8]
    )
    fig.update_layout(
        xaxis=axis,
        yaxis={**axis, "scaleanchor": "x", "scaleratio": 1},
        height=475,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="#eef2f5",
        plot_bgcolor="#eef2f5",
        shapes=shapes,
        annotations=annotations,
        uirevision="orca-v2",
        clickmode="event+select",
        hoverlabel=dict(bgcolor="white", font=dict(color="#17273d", size=12)),
    )
    return fig
