"""
config.py — Central configuration for the Conveyor Belt Metal Detection System
"""

import os
from dataclasses import dataclass, field
from typing import List

# ─────────────────────────────────────────────
#  MQTT
# ─────────────────────────────────────────────
MQTT_BROKER   = os.getenv("MQTT_BROKER",   "broker.hivemq.com")
MQTT_PORT     = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPICS   = ["metal_detector/events", "metal_detector/status"]
MQTT_CLIENT_ID = "conveyor_dashboard_v1"
MQTT_KEEPALIVE = 60
MQTT_RECONNECT_DELAY = 5   # seconds

# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "conveyor_detections.db")
DB_WRITE_BATCH_SIZE = 50       # flush every N events
DB_WRITE_INTERVAL   = 1.0      # or every N seconds

# ─────────────────────────────────────────────
#  SENSORS
# ─────────────────────────────────────────────
SENSORS: List[str] = ["LEFT", "CENTER", "RIGHT"]
SENSOR_COLORS = {
    "LEFT":   "#00d4ff",
    "CENTER": "#ff6b35",
    "RIGHT":  "#39ff14",
}

# ─────────────────────────────────────────────
#  AI / SIGNAL PROCESSING
# ─────────────────────────────────────────────
DEBOUNCE_MS          = 50      # minimum ms between events from same sensor
MIN_SIGNAL_STRENGTH  = 20      # below this → possible false detection
ANOMALY_Z_SCORE      = 3.0     # z-score threshold for anomaly flag
DRIFT_WINDOW         = 100     # last N readings for drift calculation
DRIFT_THRESHOLD      = 0.15    # relative drift (15%) triggers warning
MAINTENANCE_CYCLES   = 10_000  # expected detection cycles between maintenance

# ─────────────────────────────────────────────
#  DASHBOARD REFRESH
# ─────────────────────────────────────────────
REFRESH_INTERVAL_S = 2         # seconds between Streamlit auto-refresh
MAX_CHART_POINTS   = 500       # rolling window for live charts
MAX_LOG_ROWS       = 1_000     # rows shown in event log table

# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────
USERS = {
    "admin":    {"password": "admin123",    "role": "admin"},
    "operator": {"password": "operator123", "role": "operator"},
}
SESSION_TIMEOUT_MIN = 60

# ─────────────────────────────────────────────
#  EXPORT
# ─────────────────────────────────────────────
EXPORT_DIR = "exports"

# ─────────────────────────────────────────────
#  APP META
# ─────────────────────────────────────────────
APP_TITLE   = "ConveyorAI Monitor"
APP_VERSION = "1.0.0"
APP_ICON    = "⚡"
