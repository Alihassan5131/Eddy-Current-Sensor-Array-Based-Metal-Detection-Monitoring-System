"""
app.py — Eddy Current Conveyor Belt Metal Detection System
PIEAS Electrical Engineering Final Year Project
Authors: Ali Hassan | Maham Saeed | Muhammad Abdullah Khan
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import config
import analytics
import auth
import database
import mqtt_handler
import utils
import visualization

# ─────────────────────────────────────────────────────────────────────────────
#  BOOT
# ─────────────────────────────────────────────────────────────────────────────

utils.configure_logging()
logger = logging.getLogger("app")

st.set_page_config(
    page_title="Metal Detection Monitor — PIEAS",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg:      #080c18;
    --bg2:     #0c1020;
    --bg3:     #111828;
    --bg4:     #162035;
    --border:  #1e3050;
    --accent:  #3b82f6;
    --accent2: #06b6d4;
    --green:   #22c55e;
    --red:     #ef4444;
    --amber:   #f59e0b;
    --text:    #e2e8f0;
    --muted:   #64748b;
}

html, body, .stApp { background: var(--bg) !important; color: var(--text); font-family: 'Inter', sans-serif; }
* { font-family: 'Inter', sans-serif; }
code, .mono { font-family: 'JetBrains Mono', monospace !important; }

[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* KPI Cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-bottom: 20px;
}
.kpi-card {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 18px 16px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}
.kpi-card.total::before  { background: linear-gradient(90deg, #3b82f6, #06b6d4); }
.kpi-card.left::before   { background: #06b6d4; }
.kpi-card.center::before { background: #f97316; }
.kpi-card.right::before  { background: #22c55e; }
.kpi-card.rate::before   { background: linear-gradient(90deg, #8b5cf6, #3b82f6); }
.kpi-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
}
.kpi-value {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1;
    font-family: 'JetBrains Mono', monospace;
    word-break: break-all;
    overflow-wrap: anywhere;
}
.kpi-card.total  .kpi-value { color: #60a5fa; }
.kpi-card.left   .kpi-value { color: #06b6d4; }
.kpi-card.center .kpi-value { color: #f97316; }
.kpi-card.right  .kpi-value { color: #22c55e; }
.kpi-card.rate   .kpi-value { color: #a78bfa; }
.kpi-sub { font-size: 0.65rem; color: var(--muted); margin-top: 7px; font-family: 'JetBrains Mono', monospace; }

/* Sensor Cards */
.sensor-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 20px;
}
.sensor-card {
    background: var(--bg3);
    border-radius: 10px;
    padding: 16px 18px;
    border: 1px solid var(--border);
}
.sensor-name {
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.sensor-dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    display: inline-block;
    animation: blink 2s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
.sensor-count {
    font-size: 2rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    margin: 4px 0 6px;
    word-break: break-all;
}
.sensor-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    line-height: 1.9;
}

/* Badges */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 1px;
    font-family: 'JetBrains Mono', monospace;
}
.badge-green { background: rgba(34,197,94,0.1);  color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }
.badge-red   { background: rgba(239,68,68,0.1);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
.badge-blue  { background: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }

/* Section header */
.sec-hdr {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
    margin: 18px 0 12px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: var(--bg2); border-bottom: 1px solid var(--border); gap: 2px; }
.stTabs [data-baseweb="tab"] { color: var(--muted); font-size: 0.82rem; font-weight: 500; padding: 0.6rem 1.4rem; border-radius: 6px 6px 0 0; }
.stTabs [aria-selected="true"] { background: var(--bg3); color: var(--accent) !important; border: 1px solid var(--border); border-bottom: none; }

/* Dataframe */
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 8px; }
.stDataFrame thead th { background: var(--bg4) !important; color: var(--accent2) !important; font-size: 0.72rem; letter-spacing: 1px; }
.stDataFrame tbody td { background: var(--bg3) !important; color: var(--text) !important; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }

/* Buttons */
.stButton > button {
    background: var(--bg4); color: var(--text); border: 1px solid var(--border);
    border-radius: 7px; font-size: 0.8rem; font-weight: 500; transition: all 0.15s;
}
.stButton > button:hover { border-color: var(--accent); color: var(--accent); background: rgba(59,130,246,0.08); }

/* Event feed items */
.event-item {
    background: var(--bg3); border-left: 3px solid; border-radius: 0 6px 6px 0;
    padding: 6px 10px; margin-bottom: 5px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.63rem; line-height: 1.7;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  AUTH GATE
# ─────────────────────────────────────────────────────────────────────────────

if not auth.is_authenticated():
    auth.show_login_page()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
#  MQTT + SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

handler = mqtt_handler.get_handler()

if "live_events" not in st.session_state:
    st.session_state.live_events: List[Dict] = []
if "belt_phase" not in st.session_state:
    st.session_state.belt_phase: float = 0.0
if "active_sensors" not in st.session_state:
    st.session_state.active_sensors: List[str] = []
if "objects_on_belt" not in st.session_state:
    st.session_state.objects_on_belt: List[Dict] = []

new_events = handler.drain_queue(max_items=200)
for ev in new_events:
    enriched = analytics.process_event(ev)
    database.db.buffer_detection(enriched)
    st.session_state.live_events.append(enriched)
    if enriched["sensor"] not in st.session_state.active_sensors:
        st.session_state.active_sensors.append(enriched["sensor"])

st.session_state.live_events = st.session_state.live_events[-config.MAX_CHART_POINTS:]
st.session_state.belt_phase  = (st.session_state.belt_phase + 0.04) % 1.0

now = time.time()
st.session_state.objects_on_belt = [
    o for o in st.session_state.objects_on_belt if now - o["ts"] < 3.0
]
for ev in new_events:
    if not ev.get("is_false_det"):
        st.session_state.objects_on_belt.append({
            "x": (now % 4.0), "sensor": ev.get("sensor", "CENTER"),
            "strength": ev.get("signal_strength", 50), "ts": now,
        })

st.session_state.active_sensors = [
    s for s in st.session_state.active_sensors
    if any(e["sensor"] == s for e in st.session_state.live_events[-10:])
]

# ─────────────────────────────────────────────────────────────────────────────
#  AUTO REFRESH
# ─────────────────────────────────────────────────────────────────────────────

st_autorefresh(interval=config.REFRESH_INTERVAL_S * 1000, key="auto_refresh")

# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding:1rem 0 0.5rem'>
        <div style='font-size:1rem;font-weight:700;color:#e2e8f0;letter-spacing:0.5px'>
            Metal Detection Monitor
        </div>
        <div style='font-size:0.62rem;color:#64748b;margin-top:3px;font-family:JetBrains Mono,monospace'>
            PIEAS &nbsp;·&nbsp; EE Final Year Project
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    connected = mqtt_handler.state.connected
    badge_cls = "badge-green" if connected else "badge-red"
    badge_txt = "MQTT LIVE" if connected else "MQTT OFFLINE"
    st.markdown(f"<span class='badge {badge_cls}'>● {badge_txt}</span>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='font-family:JetBrains Mono,monospace;font-size:0.6rem;color:#64748b;margin-top:10px;line-height:2'>
    BROKER &nbsp;&nbsp;: {config.MQTT_BROKER}<br>
    PACKETS &nbsp;: {mqtt_handler.state.rx_count:,}<br>
    ERRORS &nbsp;&nbsp;: {mqtt_handler.state.error_count}<br>
    RECONNECTS: {mqtt_handler.state.reconnect_count}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"""
    <div style='font-family:JetBrains Mono,monospace;font-size:0.6rem;color:#64748b;line-height:2'>
    USER &nbsp;&nbsp;&nbsp;: {st.session_state.username.upper()}<br>
    ROLE &nbsp;&nbsp;&nbsp;: {auth.get_role().upper()}<br>
    SESSION : {analytics.get_uptime()}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if auth.is_admin():
        st.markdown("<div class='sec-hdr'>MQTT CONFIG</div>", unsafe_allow_html=True)
        new_broker = st.text_input("Broker", value=config.MQTT_BROKER)
        new_port   = st.number_input("Port", value=config.MQTT_PORT, step=1)
        if st.button("Apply & Restart"):
            config.MQTT_BROKER = new_broker
            config.MQTT_PORT   = int(new_port)
            handler.stop()
            mqtt_handler._handler = None
            st.rerun()
        st.divider()

    if st.button("Sign Out", use_container_width=True):
        auth.logout()
        st.rerun()

    st.markdown("""
    <div style='margin-top:1.5rem;padding:12px 14px;background:#0c1020;border-radius:8px;
                border:1px solid #1e3050;font-size:0.62rem;color:#64748b;line-height:2'>
        <div style='color:#94a3b8;font-weight:600;margin-bottom:4px;letter-spacing:1px;font-size:0.6rem'>
            PROJECT TEAM
        </div>
        Ali Hassan<br>
        Maham Saeed<br>
        Muhammad Abdullah Khan<br>
        <div style='margin-top:8px;color:#475569;border-top:1px solid #1e3050;padding-top:8px'>
            Electrical Engineering Dept.<br>
            PIEAS &nbsp;·&nbsp; Final Year Project 2026
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style='background:linear-gradient(135deg,#0c1020 0%,#111828 60%,#0c1828 100%);
            border:1px solid #1e3050;border-radius:12px;padding:1.4rem 2rem;
            margin-bottom:1.4rem;display:flex;align-items:center;justify-content:space-between;'>
    <div>
        <div style='font-size:1.35rem;font-weight:700;color:#e2e8f0;letter-spacing:0.3px'>
            Eddy Current Conveyor Belt Metal Detection System
        </div>
        <div style='font-size:0.68rem;color:#64748b;margin-top:5px;
                    font-family:JetBrains Mono,monospace;line-height:1.8'>
            AI-ENABLED &nbsp;·&nbsp; EDDY CURRENT SENSING &nbsp;·&nbsp; IoT (ESP32 + MQTT)
            &nbsp;·&nbsp; BELT: 17.7 cm &times; 1.5 m &nbsp;·&nbsp; SPEED: 2.0 m/s constant
        </div>
    </div>
    <div style='text-align:right;flex-shrink:0;margin-left:2rem'>
        <div style='font-size:0.8rem;font-weight:600;color:#94a3b8'>PIEAS</div>
        <div style='font-size:0.65rem;color:#64748b;font-family:JetBrains Mono,monospace;line-height:1.8'>
            Electrical Engineering<br>Final Year Project &nbsp;·&nbsp; 2026
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

kpi        = database.db.get_kpi_summary()
live       = pd.DataFrame(st.session_state.live_events) if st.session_state.live_events else pd.DataFrame()
total      = kpi["total"]
per_sensor = kpi["per_sensor"]
last_hour  = kpi["last_hour"]
det_rate   = round(last_hour / 60, 1)

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card total">
        <div class="kpi-label">Total Detections</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-sub">all sensors &nbsp;·&nbsp; all time</div>
    </div>
    <div class="kpi-card left">
        <div class="kpi-label">Left Sensor</div>
        <div class="kpi-value">{per_sensor.get('LEFT', 0)}</div>
        <div class="kpi-sub">GPIO 25 &nbsp;·&nbsp; tunnel left</div>
    </div>
    <div class="kpi-card center">
        <div class="kpi-label">Center Sensor</div>
        <div class="kpi-value">{per_sensor.get('CENTER', 0)}</div>
        <div class="kpi-sub">GPIO 32 &nbsp;·&nbsp; tunnel center</div>
    </div>
    <div class="kpi-card right">
        <div class="kpi-label">Right Sensor</div>
        <div class="kpi-value">{per_sensor.get('RIGHT', 0)}</div>
        <div class="kpi-sub">GPIO 33 &nbsp;·&nbsp; tunnel right</div>
    </div>
    <div class="kpi-card rate">
        <div class="kpi-label">Detection Rate</div>
        <div class="kpi-value">{det_rate}</div>
        <div class="kpi-sub">detections / min &nbsp;·&nbsp; last hour</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SENSOR STATUS CARDS
# ─────────────────────────────────────────────────────────────────────────────

health_data  = analytics.get_sensor_health()
health_map   = {h["sensor"]: h for h in health_data}
sensor_color = {"LEFT": "#06b6d4", "CENTER": "#f97316", "RIGHT": "#22c55e"}
sensor_gpio  = {"LEFT": "GPIO 25", "CENTER": "GPIO 32",  "RIGHT": "GPIO 33"}
sensor_pos   = {"LEFT": "Tunnel — Left",  "CENTER": "Tunnel — Center", "RIGHT": "Tunnel — Right"}

cards = '<div class="sensor-grid">'
for s in ["LEFT", "CENTER", "RIGHT"]:
    h      = health_map.get(s, {})
    color  = sensor_color[s]
    count  = h.get("total_detections", 0)
    active = s in st.session_state.active_sensors
    badge  = (f"<span class='badge badge-green'>ACTIVE</span>" if active
              else f"<span class='badge badge-blue'>STANDBY</span>")
    cards += f"""
    <div class="sensor-card" style="border-left:3px solid {color}">
        <div class="sensor-name">
            <span class="sensor-dot" style="background:{color}"></span>
            <span style="color:{color}">{s} SENSOR</span>
            &nbsp;{badge}
        </div>
        <div class="sensor-count" style="color:{color}">{count}</div>
        <div class="sensor-meta">
            PIN &nbsp;&nbsp;&nbsp;: {sensor_gpio[s]}<br>
            MOUNT : {sensor_pos[s]}<br>
            TYPE &nbsp;: Eddy Current
        </div>
    </div>"""
cards += '</div>'
st.markdown(cards, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────────────────

tabs = st.tabs([
    "🎯  3D Belt View",
    "📈  Charts",
    "📋  Event Log",
    "⚙️  Admin" if auth.is_admin() else "ℹ️  Info",
])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 0 — 3D BELT
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("<div class='sec-hdr'>3D Conveyor Belt — Live View</div>", unsafe_allow_html=True)
        fig_3d = visualization.build_3d_conveyor(
            active_sensors=st.session_state.active_sensors,
            objects=st.session_state.objects_on_belt,
            belt_offset=st.session_state.belt_phase,
        )
        st.plotly_chart(fig_3d, use_container_width=True, key="belt3d")

        st.markdown("""
        <div style='display:flex;gap:28px;padding:10px 16px;background:#0c1020;
                    border-radius:8px;border:1px solid #1e3050'>
            <div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:#64748b'>
                WIDTH &nbsp;<span style='color:#e2e8f0;font-weight:600'>17.7 cm</span>
            </div>
            <div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:#64748b'>
                LENGTH &nbsp;<span style='color:#e2e8f0;font-weight:600'>1.5 m</span>
            </div>
            <div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:#64748b'>
                SPEED &nbsp;<span style='color:#e2e8f0;font-weight:600'>2.0 m/s (constant)</span>
            </div>
            <div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:#64748b'>
                SENSORS &nbsp;<span style='color:#e2e8f0;font-weight:600'>Stationary — Tunnel Mount</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='sec-hdr'>Live Event Feed</div>", unsafe_allow_html=True)
        if st.session_state.live_events:
            for ev in reversed(st.session_state.live_events[-12:]):
                s      = ev.get("sensor", "?")
                color  = sensor_color.get(s, "#888")
                sig    = ev.get("signal_strength", 0)
                ts_str = utils.fmt_ts(ev.get("timestamp", ""))
                obj_id = ev.get("object_id", "-")
                st.markdown(f"""
                <div class='event-item' style='border-color:{color}'>
                    <span style='color:{color};font-weight:600'>{s}</span>
                    &nbsp;<span style='color:#94a3b8'>#{obj_id}</span><br>
                    <span style='color:#64748b'>SIG:{sig} &nbsp;{ts_str}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='color:#64748b;font-size:0.72rem;font-family:JetBrains Mono,monospace;
                        padding:14px;border:1px dashed #1e3050;border-radius:6px;text-align:center'>
                Awaiting detections...
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div class='sec-hdr'>Connection</div>", unsafe_allow_html=True)
        connected = mqtt_handler.state.connected
        st.markdown(
            f"<span class='badge {'badge-green' if connected else 'badge-red'}'>"
            f"{'● MQTT LIVE' if connected else '● OFFLINE'}</span>",
            unsafe_allow_html=True
        )
        st.markdown(f"""
        <div style='font-family:JetBrains Mono,monospace;font-size:0.6rem;
                    color:#64748b;margin-top:8px;line-height:2'>
        RX: {mqtt_handler.state.rx_count:,} packets<br>
        ERR: {mqtt_handler.state.error_count}
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — CHARTS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("<div class='sec-hdr'>Detection Charts</div>", unsafe_allow_html=True)

    if live.empty:
        st.info("No data yet — trigger a sensor or use the simulator below.")
    else:
        st.plotly_chart(visualization.build_timeline_chart(live),
                        use_container_width=True, key="timeline")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.plotly_chart(visualization.build_sensor_activity(live),
                            use_container_width=True, key="activity")
        with cc2:
            st.plotly_chart(visualization.build_heatmap(live),
                            use_container_width=True, key="heatmap")

    st.divider()
    st.markdown("<div class='sec-hdr'>Event Simulator — Testing Only</div>", unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        sim_sensor   = st.selectbox("Sensor", config.SENSORS, key="sim_sensor")
    with s2:
        sim_strength = st.slider("Signal Strength", 10, 100, 75, key="sim_str")

    if st.button("Inject Detection", use_container_width=True):
        fake_event = {
            "device_id": "SIM_01", "event": "DETECTION",
            "sensor": sim_sensor, "timestamp": datetime.utcnow().isoformat(),
            "strength": sim_strength, "duration_ms": 12,
            "belt_speed": 2.0, "object_id": int(time.time()) % 99999,
        }
        enriched = analytics.process_event(fake_event)
        database.db.buffer_detection(enriched)
        st.session_state.live_events.append(enriched)
        st.success(f"Injected {sim_sensor} detection (strength={sim_strength})")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — EVENT LOG
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<div class='sec-hdr'>Detection Event Log</div>", unsafe_allow_html=True)

    rows   = database.db.get_recent_detections(limit=config.MAX_LOG_ROWS)
    df_log = pd.DataFrame(rows) if rows else pd.DataFrame()

    if df_log.empty:
        st.info("No records yet.")
    else:
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            sel_sensors = st.multiselect("Filter Sensor",
                config.SENSORS, default=config.SENSORS, key="log_sensor")
        with fc2:
            sig_min = st.slider("Min Signal Strength", 0, 100, 0, key="log_sig")
        with fc3:
            n_rows = st.number_input("Rows", 10, 1000, 100, step=10, key="log_n")

        mask        = df_log["sensor"].isin(sel_sensors) & (df_log["signal_strength"] >= sig_min)
        df_filtered = df_log[mask].head(int(n_rows))

        # Columns: no belt_speed, no is_anomaly
        display_cols = ["timestamp", "sensor", "object_id", "signal_strength", "duration_ms", "is_false_det"]
        df_display   = df_filtered[[c for c in display_cols if c in df_filtered.columns]].copy()
        df_display.columns = ["Timestamp", "Sensor", "Object ID", "Signal Strength", "Duration (ms)", "False Det"]
        df_display["Timestamp"] = df_display["Timestamp"].apply(
            lambda x: utils.fmt_ts(str(x)) if pd.notna(x) else x
        )

        st.dataframe(df_display, use_container_width=True, height=430)
        st.caption(
            f"Showing {len(df_display):,} of {len(df_log):,} records  ·  "
            f"Total in DB: {database.db.get_db_stats()['total_records']:,}"
        )

        st.markdown("<div class='sec-hdr'>Export</div>", unsafe_allow_html=True)
        e1, e2, e3 = st.columns(3)
        with e1:
            csv_data = utils.export_csv(df_filtered.to_dict("records"))
            st.download_button("Download CSV", csv_data,
                "detections.csv", "text/csv", use_container_width=True)
        with e2:
            try:
                xl_data = utils.export_excel(df_filtered.to_dict("records"))
                st.download_button("Download Excel", xl_data,
                    "detections.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)
            except Exception:
                st.button("Excel (install openpyxl)", disabled=True, use_container_width=True)
        with e3:
            try:
                stats_for_pdf = analytics.compute_dataframe_analytics(df_filtered)
                pdf_data = utils.export_pdf_report(stats_for_pdf, df_filtered.to_dict("records"))
                if isinstance(pdf_data, bytes) and pdf_data[:4] == b"%PDF":
                    st.download_button("Download PDF Report", pdf_data,
                        "detection_report.pdf", "application/pdf", use_container_width=True)
                else:
                    st.button("PDF (unavailable)", disabled=True, use_container_width=True)
            except Exception:
                st.button("PDF (unavailable)", disabled=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — ADMIN / INFO
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    if auth.is_admin():
        st.markdown("<div class='sec-hdr'>Admin Panel</div>", unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("**System Settings**")
            new_debounce = st.number_input("Debounce (ms)", value=config.DEBOUNCE_MS, step=5)
            new_min_sig  = st.number_input("Min Signal Strength", value=config.MIN_SIGNAL_STRENGTH, step=5)
            new_refresh  = st.number_input("Refresh Interval (s)", value=config.REFRESH_INTERVAL_S, step=1)
            if st.button("Apply Settings"):
                config.DEBOUNCE_MS         = int(new_debounce)
                config.MIN_SIGNAL_STRENGTH = int(new_min_sig)
                config.REFRESH_INTERVAL_S  = int(new_refresh)
                st.success("Settings applied.")
        with a2:
            st.markdown("**Database**")
            db_stats = database.db.get_db_stats()
            st.metric("Total Records", f"{db_stats['total_records']:,}")
            st.metric("Database Size", f"{db_stats['size_kb']:,} KB")
            if st.button("Force Flush Buffer"):
                database.db.force_flush()
                st.success("Buffer flushed.")
            if st.button("Clear All Data", type="primary"):
                with database.db._connect() as conn:
                    conn.execute("DELETE FROM detections")
                    conn.execute("UPDATE sensor_health SET total_detections=0, avg_strength=0")
                st.warning("Database cleared.")
                st.rerun()
        st.divider()
        st.markdown(f"**MQTT Topics:** `{', '.join(config.MQTT_TOPICS)}`")
        st.markdown(f"**Queue depth:** `{mqtt_handler.event_queue.qsize()}`")

    else:
        st.markdown("<div class='sec-hdr'>System Information</div>", unsafe_allow_html=True)
        st.markdown(f"""
| Field | Value |
|-------|-------|
| Project | Eddy Current Conveyor Belt Metal Detection System |
| Department | Electrical Engineering — PIEAS |
| Team | Ali Hassan &nbsp;·&nbsp; Maham Saeed &nbsp;·&nbsp; Muhammad Abdullah Khan |
| MQTT Broker | {config.MQTT_BROKER}:{config.MQTT_PORT} |
| Belt Dimensions | 17.7 cm × 1.5 m |
| Belt Speed | 2.0 m/s (constant) |
| Sensor Config | LEFT · CENTER · RIGHT — Tunnel Mount, Stationary |
| App Version | {config.APP_VERSION} |
        """)