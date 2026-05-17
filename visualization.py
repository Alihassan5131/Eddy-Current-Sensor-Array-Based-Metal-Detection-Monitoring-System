"""
visualization.py — Plotly/PyDeck charts and 3D conveyor belt simulation
"""

from __future__ import annotations
import math
import time
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import config

# ─────────────────────────────────────────────────────────────────────────────
#  THEME TOKENS
# ─────────────────────────────────────────────────────────────────────────────

DARK_BG    = "#0a0e1a"
GRID_COLOR = "#1e2740"
TEXT_COLOR = "#c8d8f0"
ACCENT     = "#00d4ff"
DANGER     = "#ff4757"
SUCCESS    = "#39ff14"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=DARK_BG,
    plot_bgcolor=DARK_BG,
    font=dict(color=TEXT_COLOR, family="'Share Tech Mono', monospace", size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
)

SENSOR_COLORS = config.SENSOR_COLORS   # {"LEFT": ..., "CENTER": ..., "RIGHT": ...}

# ─────────────────────────────────────────────────────────────────────────────
#  3-D CONVEYOR BELT
# ─────────────────────────────────────────────────────────────────────────────

def build_3d_conveyor(
    active_sensors: List[str],
    objects: Optional[List[Dict]] = None,
    belt_offset: float = 0.0,   # 0–1, animated scrolling
) -> go.Figure:
    """
    Render an industrial-style 3-D conveyor belt with tunnel detector.
    active_sensors: list of currently glowing sensors
    objects: [{x, sensor, strength}] metallic blobs on the belt
    belt_offset: scrolling phase (0–1)
    """
    fig = go.Figure()

    # ── Belt surface (moving stripes) ─────────────────────────────────────────
    belt_len  = 4.0
    belt_w    = 1.2
    stripe_n  = 20
    xs = np.linspace(0, belt_len, 200)
    ys = np.linspace(-belt_w / 2, belt_w / 2, 10)
    X, Y = np.meshgrid(xs, ys)
    Z = np.zeros_like(X)
    stripe = (np.sin((X / belt_len * stripe_n + belt_offset) * 2 * math.pi) * 0.5 + 0.5)
    fig.add_trace(go.Surface(
        x=X, y=Y, z=Z,
        surfacecolor=stripe,
        colorscale=[[0, "#1a2035"], [1, "#243055"]],
        showscale=False,
        opacity=0.9,
        name="Belt",
    ))

    # ── Tunnel frame ──────────────────────────────────────────────────────────
    tunnel_x = belt_len / 2
    tunnel_h  = 0.8
    # four vertical pillars
    for dy in [-belt_w / 2 - 0.1, belt_w / 2 + 0.1]:
        fig.add_trace(go.Scatter3d(
            x=[tunnel_x, tunnel_x],
            y=[dy, dy],
            z=[0, tunnel_h],
            mode="lines",
            line=dict(color="#4a6080", width=6),
            showlegend=False,
        ))
    # top beam
    fig.add_trace(go.Scatter3d(
        x=[tunnel_x, tunnel_x],
        y=[-belt_w / 2 - 0.1, belt_w / 2 + 0.1],
        z=[tunnel_h, tunnel_h],
        mode="lines",
        line=dict(color="#4a6080", width=6),
        showlegend=False,
    ))

    # ── Sensor pods ───────────────────────────────────────────────────────────
    sensor_pos = {
        "LEFT":   (tunnel_x, -belt_w / 2,     tunnel_h - 0.1),
        "CENTER": (tunnel_x,  0,               tunnel_h),
        "RIGHT":  (tunnel_x,  belt_w / 2,      tunnel_h - 0.1),
    }
    for name, (sx, sy, sz) in sensor_pos.items():
        is_active = name in active_sensors
        color = SENSOR_COLORS[name] if is_active else "#334466"
        size  = 14 if is_active else 8
        fig.add_trace(go.Scatter3d(
            x=[sx], y=[sy], z=[sz],
            mode="markers+text",
            marker=dict(size=size, color=color,
                        line=dict(width=2, color="#ffffff") if is_active else dict(width=0)),
            text=[name],
            textposition="top center",
            textfont=dict(color=color, size=10),
            name=f"Sensor {name}",
            showlegend=False,
        ))

        # detection beam
        if is_active:
            for bz in np.linspace(0, sz, 12):
                alpha = 1 - bz / sz
                fig.add_trace(go.Scatter3d(
                    x=[sx], y=[sy], z=[bz],
                    mode="markers",
                    marker=dict(size=3 * alpha + 1, color=color, opacity=alpha * 0.6),
                    showlegend=False,
                ))

    # ── Metallic objects on belt ───────────────────────────────────────────────
    for obj in (objects or []):
        ox   = obj.get("x", belt_len / 2)
        col  = SENSOR_COLORS.get(obj.get("sensor", "CENTER"), "#aaaaaa")
        size = max(4, min(14, obj.get("strength", 50) / 8))
        fig.add_trace(go.Scatter3d(
            x=[ox], y=[0], z=[0.05],
            mode="markers",
            marker=dict(
                size=size,
                color=col,
                symbol="circle",
                opacity=0.9,
                line=dict(width=1, color="#ffffff"),
            ),
            showlegend=False,
        ))

    # ── Axis cosmetics ────────────────────────────────────────────────────────
    fig.update_layout(
        paper_bgcolor=DARK_BG,
        scene=dict(
            bgcolor=DARK_BG,
            xaxis=dict(title="Belt Length (m)", color=TEXT_COLOR,
                       backgroundcolor=DARK_BG, gridcolor=GRID_COLOR),
            yaxis=dict(title="Width (m)", color=TEXT_COLOR,
                       backgroundcolor=DARK_BG, gridcolor=GRID_COLOR),
            zaxis=dict(title="Height (m)", color=TEXT_COLOR,
                       backgroundcolor=DARK_BG, gridcolor=GRID_COLOR, range=[0, 1.2]),
            camera=dict(eye=dict(x=1.6, y=-1.8, z=1.1)),
            aspectratio=dict(x=2, y=1, z=0.5),
        ),
        margin=dict(l=0, r=0, t=20, b=0),
        height=420,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  TIMELINE CHART
# ─────────────────────────────────────────────────────────────────────────────

def build_timeline_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("No detection data yet")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    fig = go.Figure()
    for sensor in config.SENSORS:
        sub = df[df["sensor"] == sensor]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["timestamp"],
            y=sub["signal_strength"],
            mode="markers+lines",
            name=sensor,
            line=dict(color=SENSOR_COLORS[sensor], width=1.5),
            marker=dict(size=4, color=SENSOR_COLORS[sensor]),
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Detection Timeline — Signal Strength",
        xaxis_title="Time",
        yaxis_title="Signal Strength",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        height=320,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  SENSOR ACTIVITY BAR
# ─────────────────────────────────────────────────────────────────────────────

def build_sensor_activity(df: pd.DataFrame) -> go.Figure:
    counts = {s: 0 for s in config.SENSORS}
    if not df.empty:
        vc = df["sensor"].value_counts()
        for s in config.SENSORS:
            counts[s] = int(vc.get(s, 0))

    fig = go.Figure(go.Bar(
        x=list(counts.keys()),
        y=list(counts.values()),
        marker_color=[SENSOR_COLORS[s] for s in counts],
        marker_line_color="#ffffff",
        marker_line_width=0.5,
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Sensor Detection Count",
        xaxis_title="Sensor",
        yaxis_title="Detections",
        height=300,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  HEATMAP  (hour × sensor)
# ─────────────────────────────────────────────────────────────────────────────

def build_heatmap(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("Awaiting data for heatmap")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["hour"] = df["timestamp"].dt.hour

    pivot = df.groupby(["hour", "sensor"]).size().reset_index(name="count")
    pivot = pivot.pivot(index="sensor", columns="hour", values="count").fillna(0)

    # ensure all sensors are present
    for s in config.SENSORS:
        if s not in pivot.index:
            pivot.loc[s] = 0
    pivot = pivot.reindex(config.SENSORS)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index.tolist(),
        colorscale=[[0, DARK_BG], [0.5, "#1a4a8a"], [1, ACCENT]],
        showscale=True,
        colorbar=dict(tickfont=dict(color=TEXT_COLOR)),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Detection Heatmap (Hour of Day × Sensor)",
        xaxis_title="Hour",
        yaxis_title="Sensor",
        height=280,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  THROUGHPUT
# ─────────────────────────────────────────────────────────────────────────────

def build_throughput(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("No throughput data")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    df = df.set_index("timestamp")

    rate = df["belt_speed"].resample("1min").mean()

    fig = go.Figure(go.Scatter(
        x=rate.index,
        y=rate.values,
        fill="tozeroy",
        fillcolor=f"rgba(0,212,255,0.15)",
        line=dict(color=ACCENT, width=2),
        name="Belt Speed (m/s)",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Conveyor Belt Speed Over Time",
        xaxis_title="Time",
        yaxis_title="Speed (m/s)",
        height=280,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  GAUGE — detection rate
# ─────────────────────────────────────────────────────────────────────────────

def build_rate_gauge(rate: float, max_rate: float = 60.0) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=rate,
        title=dict(text="Detections / min", font=dict(color=TEXT_COLOR, size=14)),
        number=dict(font=dict(color=ACCENT, size=28)),
        delta=dict(reference=max_rate / 2, increasing=dict(color=SUCCESS),
                   decreasing=dict(color=DANGER)),
        gauge=dict(
            axis=dict(range=[0, max_rate], tickcolor=TEXT_COLOR,
                      tickfont=dict(color=TEXT_COLOR)),
            bar=dict(color=ACCENT),
            bgcolor=GRID_COLOR,
            borderwidth=1,
            bordercolor=GRID_COLOR,
            steps=[
                dict(range=[0, max_rate * 0.4], color="#0d1b2a"),
                dict(range=[max_rate * 0.4, max_rate * 0.75], color="#0f2a3a"),
                dict(range=[max_rate * 0.75, max_rate], color="#1a0a0a"),
            ],
            threshold=dict(line=dict(color=DANGER, width=3),
                           thickness=0.75, value=max_rate * 0.9),
        ),
    ))
    fig.update_layout(
        paper_bgcolor=DARK_BG,
        font=dict(color=TEXT_COLOR),
        height=240,
        margin=dict(l=20, r=20, t=30, b=10),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _empty_fig(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(color=TEXT_COLOR, size=14),
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=280)
    return fig
