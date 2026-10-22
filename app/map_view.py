"""Grid map of the town (Plotly): hospitals, calls, and units at their logical place.

There is no live vehicle tracking: a unit is drawn at its station, at the call it serves, or at
the hospital it is delivering to.
"""

from __future__ import annotations

import plotly.graph_objects as go

from app.state import DashState
from sim.town import TownProfile

SEVERITY_COLOR = {"CRITICAL": "#E5484D", "SERIOUS": "#F08C2E", "MINOR": "#E6C229",
                  "EXPECTANT": "#8B8D98"}
UNIT_GROUPS = {
    "IDLE": ("Available", "#3DD68C"),
    "EN_ROUTE": ("Going to call", "#4C9EFF"),
    "STAGING": ("Staging (unsafe scene)", "#B18CFF"),
    "ON_SCENE": ("On scene", "#B18CFF"),
    "LOADING": ("On scene", "#B18CFF"),
    "TRANSPORTING": ("Transporting", "#E5484D"),
    "WAITING_AT_ER": ("Waiting at ER door", "#F2A33A"),
    "HANDOVER": ("Waiting at ER door", "#F2A33A"),
    "RETURNING": ("Returning", "#8B8D98"),
}
GRID, MAJOR, TEXT, BG = "rgba(140,160,180,0.14)", "rgba(140,160,180,0.32)", "#C9D3DD", "#111A23"


def _hospital_color(h: dict) -> str:
    occ = h["er_occupancy"]
    if occ >= 1.0 or h.get("queue_scenario", 0) or h.get("boarding", 0):
        return "#E5484D"
    return "#F2A33A" if occ >= 0.8 else "#3DD68C"


def town_map(state: DashState, town: TownProfile) -> go.Figure:
    size = town.area_km
    fig = go.Figure()

    # Calls: size by victims, color by worst severity; hollow once nobody waits on scene.
    for inc in state.incidents.values():
        x, y = town.to_km(*inc["location"])
        worst = next((s for s in SEVERITY_COLOR if s in inc["severities"]), "MINOR")
        waiting = inc["waiting"] > 0
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", showlegend=False,
            marker=dict(size=10 + 2.2 * min(inc["victims"], 20),
                        color=SEVERITY_COLOR[worst] if waiting else "rgba(0,0,0,0)",
                        line=dict(color=SEVERITY_COLOR[worst], width=2), opacity=0.85,
                        symbol="x" if inc["violent"] and not inc["secured"] else "circle"),
            text=[inc["id"]], textposition="top center", textfont=dict(color=TEXT, size=10),
            hovertemplate=(f"<b>{inc['id']}</b> {inc['type'].replace('_', ' ').lower()}<br>"
                           f"victims {inc['victims']} (reported {inc['reported']})<br>"
                           f"waiting on scene {inc['waiting']}<extra></extra>"),
        ))

    # Hospitals: labeled squares colored by ER pressure.
    for hid, h in sorted(state.hospitals.items()):
        x, y = town.to_km(*h["location"])
        occ, tot = h["occupied"], h["totals"]
        label = (f"{hid}  ER {occ['er_bed']}/{tot['er_bed']}  "
                 f"ward {occ['ward_bed']}/{tot['ward_bed']}")
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", showlegend=False,
            marker=dict(symbol="square", size=26, color=_hospital_color(h),
                        line=dict(color="#0B1117", width=2)),
            text=[f"<b>{label}</b>"], textposition="bottom center",
            textfont=dict(color=TEXT, size=11),
            hovertemplate=(f"<b>Hospital {hid}</b><br>ER {occ['er_bed']}/{tot['er_bed']}, "
                           f"queue {h['queue_scenario']}, boarding {h.get('boarding', 0)}<br>"
                           f"trauma bays {occ['trauma_bay']}/{tot['trauma_bay']}, "
                           f"surgeons {occ['surgeon']}/{tot['surgeon']}<br>"
                           f"ambulances at door {h['ambulances_waiting']}<extra></extra>"),
        ))

    # Units: grouped by status; small offsets so units at one place don't overlap.
    groups: dict[str, list] = {}
    placed: dict[tuple, int] = {}
    for uid, u in sorted(state.units.items()):
        if not u.get("activated") or not u.get("location"):
            continue
        x, y = town.to_km(*u["location"])
        k = placed.get((round(x, 2), round(y, 2)), 0)
        placed[(round(x, 2), round(y, 2))] = k + 1
        label, color = UNIT_GROUPS.get(u["state"], (u["state"], "#8B8D98"))
        groups.setdefault(label, [color, [], [], []])
        g = groups[label]
        g[1].append(x + 0.45 + 0.42 * (k % 3))
        g[2].append(y + 0.45 + 0.42 * (k // 3))
        g[3].append(uid)
    for label, (color, xs, ys, ids) in groups.items():
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name=label,
            marker=dict(symbol="triangle-up", size=11, color=color,
                        line=dict(color="#0B1117", width=1)),
            text=ids, hovertemplate="%{text}<extra>" + label + "</extra>",
        ))

    axis = dict(range=[-0.5, size + 0.5], dtick=1, gridcolor=GRID, zeroline=False,
                showline=False, tickfont=dict(color="#7D8A97", size=9), fixedrange=True)
    fig.update_layout(
        xaxis={**axis, "title": dict(text="km east", font=dict(color="#7D8A97", size=10))},
        yaxis={**axis, "title": dict(text="km north", font=dict(color="#7D8A97", size=10)),
               "scaleanchor": "x", "scaleratio": 1},
        plot_bgcolor=BG, paper_bgcolor="rgba(0,0,0,0)", height=560,
        margin=dict(l=40, r=10, t=10, b=40),
        legend=dict(orientation="h", y=-0.12, font=dict(color=TEXT, size=11),
                    bgcolor="rgba(0,0,0,0)"),
        shapes=[dict(type="line", x0=v, x1=v, y0=0, y1=size, line=dict(color=MAJOR, width=1))
                for v in range(0, int(size) + 1, 5)] +
               [dict(type="line", y0=v, y1=v, x0=0, x1=size, line=dict(color=MAJOR, width=1))
                for v in range(0, int(size) + 1, 5)],
    )
    return fig
