"""Dispatch map of the town (Plotly): street grid, stations, hospitals, calls, and units.

There is no live vehicle tracking: a unit is drawn at its station, at the call it serves, or at
the hospital it is delivering to. Assignment lines show where a unit is headed.
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
HOSPITAL_COLOR = {"OPEN": "#3DD68C", "BUSY": "#F2A33A", "SATURATED": "#E5484D"}
BG, STREET, ARTERIAL, HIGHWAY = "#0B1016", "rgba(120,140,160,0.16)", \
    "rgba(120,140,160,0.32)", "rgba(150,170,190,0.45)"
REACH = 25  # km of surrounding area drawn beyond the town limits, so the map fills its panel
TEXT, MUTED, STATION = "#C9D3DD", "#7D8A97", "#E6C229"
LAYERS = ("Street grid", "Stations", "Routes", "Labels")


def _streets(size: float) -> list[dict]:
    """1 km blocks, brighter arterials every 5 km, and two diagonal highways.

    Streets inside the town are drawn brighter than the surrounding area.
    """
    shapes = []
    lo, hi = -REACH, int(size) + REACH
    for v in range(lo, hi + 1):
        major = v % 5 == 0
        inside = 0 <= v <= size
        style = dict(color=ARTERIAL if major else STREET, width=1.6 if major else 0.7)
        faint = dict(color="rgba(120,140,160,0.07)", width=1 if major else 0.5)
        shapes.append(dict(type="line", x0=v, x1=v, y0=lo, y1=hi, line=faint, layer="below"))
        shapes.append(dict(type="line", y0=v, y1=v, x0=lo, x1=hi, line=faint, layer="below"))
        if inside:
            shapes.append(dict(type="line", x0=v, x1=v, y0=0, y1=size, line=style,
                               layer="below"))
            shapes.append(dict(type="line", y0=v, y1=v, x0=0, x1=size, line=style,
                               layer="below"))
    hw = dict(color=HIGHWAY, width=3)
    for (ax, ay), (bx, by) in (((0, 0.15), (1, 0.85)), ((0.1, 1), (0.9, 0))):
        slope = (by - ay) / (bx - ax)  # extend each highway across the whole drawn area
        shapes.append(dict(type="line", x0=lo, y0=size * ay + slope * (lo - size * ax),
                           x1=hi, y1=size * ay + slope * (hi - size * ax), line=hw,
                           layer="below"))
    shapes.append(dict(type="rect", x0=0, y0=0, x1=size, y1=size, layer="below",
                       line=dict(color="rgba(76,158,255,0.35)", width=1.2, dash="dot")))
    return shapes


def _route(fig: go.Figure, a: tuple, b: tuple, color: str, dash: str) -> None:
    fig.add_trace(go.Scatter(x=[a[0], b[0]], y=[a[1], b[1]], mode="lines", showlegend=False,
                             hoverinfo="skip", line=dict(color=color, width=2, dash=dash),
                             opacity=0.75))


def town_map(state: DashState, town: TownProfile, focus: str | None = None,
             height: int = 640, layers: set[str] | None = None) -> go.Figure:
    layers = set(LAYERS) if layers is None else layers
    size = town.area_km
    labels = "Labels" in layers
    fig = go.Figure()

    # Ambulance stations (home bases), drawn under everything else.
    if "Stations" in layers:
        homes = {tuple(u["home"]) for u in state.units.values()
                 if u.get("home") and u.get("activated")}
        if homes:
            pts = [town.to_km(*h) for h in sorted(homes)]
            fig.add_trace(go.Scatter(
                x=[p[0] for p in pts], y=[p[1] for p in pts], mode="markers", name="Station",
                marker=dict(symbol="diamond", size=9, color=STATION,
                            line=dict(color=BG, width=1)),
                hovertemplate="Ambulance station<extra></extra>"))

    # Assignment lines: station -> call while en route, call -> hospital while transporting.
    if "Routes" in layers:
        for u in state.units.values():
            inc = state.incidents.get(u.get("incident_id") or "")
            if u["state"] == "EN_ROUTE" and inc and u.get("home"):
                _route(fig, town.to_km(*u["home"]), town.to_km(*inc["location"]),
                       "#4C9EFF", "dot")
            elif u["state"] == "TRANSPORTING" and inc and u.get("hospital_id") in state.hospitals:
                _route(fig, town.to_km(*inc["location"]),
                       town.to_km(*state.hospitals[u["hospital_id"]]["location"]),
                       "#E5484D", "dash")

    # Calls: size by victims, color by worst severity; hollow once nobody waits on scene.
    for inc in state.incidents.values():
        x, y = town.to_km(*inc["location"])
        worst = next((s for s in SEVERITY_COLOR if s in inc["severities"]), "MINOR")
        color = SEVERITY_COLOR[worst]
        waiting = inc["waiting"] > 0
        ring = 22 + 2.2 * min(inc["victims"], 20)
        if waiting:  # soft halo so active calls stand out on the dark map
            fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", showlegend=False,
                                     hoverinfo="skip", marker=dict(size=ring + 14, color=color,
                                                                   opacity=0.18)))
        if inc["id"] == focus:
            fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", showlegend=False,
                                     hoverinfo="skip",
                                     marker=dict(size=ring + 8, color="rgba(0,0,0,0)",
                                                 line=dict(color="#4C9EFF", width=3))))
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text" if labels else "markers", showlegend=False,
            marker=dict(size=10 + 2.2 * min(inc["victims"], 20),
                        color=color if waiting else "rgba(0,0,0,0)",
                        line=dict(color=color, width=2), opacity=0.9,
                        symbol="x" if inc["violent"] and not inc["secured"] else "circle"),
            text=[f"<b>{inc['id']}</b>"], textposition="top center",
            textfont=dict(color=TEXT, size=11),
            hovertemplate=(f"<b>{inc['id']}</b> {inc['type'].replace('_', ' ').lower()}<br>"
                           f"victims {inc['victims']} (reported {inc['reported']})<br>"
                           f"waiting on scene {inc['waiting']}<extra></extra>"),
        ))

    # Hospitals: a white cross on a disc colored by board status.
    for hid, h in sorted(state.hospitals.items()):
        x, y = town.to_km(*h["location"])
        occ, tot = h["occupied"], h["totals"]
        er_free, ward_free = tot["er_bed"] - occ["er_bed"], tot["ward_bed"] - occ["ward_bed"]
        color = HOSPITAL_COLOR.get(h.get("status", "OPEN"), "#3DD68C")
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers", showlegend=False, hoverinfo="skip",
            marker=dict(size=28, color=color, line=dict(color=BG, width=2))))
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text" if labels else "markers", showlegend=False,
            marker=dict(symbol="cross-thin", size=14, line=dict(color="white", width=3.5)),
            text=[f"<b>HOSPITAL {hid}</b><br>ER {er_free} free · ward {ward_free} free"],
            textposition="bottom center", textfont=dict(color=TEXT, size=10),
            hovertemplate=(f"<b>{h.get('name', 'Hospital ' + hid)}</b> · {h.get('status')}<br>"
                           f"ER free {er_free}/{tot['er_bed']}, waiting {h['queue_scenario']}, "
                           f"boarding {h.get('boarding', 0)}<br>"
                           f"ward free {ward_free}/{tot['ward_bed']}<br>"
                           f"trauma bays {occ['trauma_bay']}/{tot['trauma_bay']} used, "
                           f"surgeons {occ['surgeon']}/{tot['surgeon']} busy<br>"
                           f"incoming {h.get('incoming', 0)}, "
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
        g[1].append(x + 0.55 + 0.5 * (k % 3))
        g[2].append(y + 0.55 + 0.5 * (k // 3))
        g[3].append(uid)
    for label, (color, xs, ys, ids) in groups.items():
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text" if labels else "markers", name=label,
            marker=dict(symbol="triangle-up", size=13, color=color,
                        line=dict(color=BG, width=1)),
            text=ids, textposition="middle right", textfont=dict(color=MUTED, size=9),
            hovertemplate="%{text}<extra>" + label + "</extra>",
        ))

    axis = dict(showgrid=False, zeroline=False, showline=False, showticklabels=False,
                fixedrange=True)
    fig.update_layout(  # y shows the whole town; x widens to fill the panel at 1:1 scale
        xaxis={**axis, "range": [-1, size + 1], "constrain": "range"},
        yaxis={**axis, "range": [-1, size + 1], "scaleanchor": "x", "scaleratio": 1},
        showlegend=False,
        plot_bgcolor=BG, paper_bgcolor=BG, height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        shapes=_streets(size) if "Street grid" in layers else [],
        annotations=[dict(  # scale bar caption
            x=size, y=-0.6, xanchor="right", showarrow=False,
            text=f"Town limits {size:.0f} × {size:.0f} km (dotted) · 1 block = 1 km",
            font=dict(color=MUTED, size=10))],
    )
    return fig
