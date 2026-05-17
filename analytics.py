"""
analytics.py — AI/ML analytics: anomaly detection, sensor drift, predictive maintenance
"""

import logging
from collections import deque, defaultdict
from datetime import datetime
from typing import Dict, List, Deque, Tuple, Any, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  ROLLING BUFFERS  (per-sensor)
# ─────────────────────────────────────────────────────────────────────────────

class SensorBuffer:
    def __init__(self, maxlen: int = config.DRIFT_WINDOW):
        self.strengths: Deque[float]    = deque(maxlen=maxlen)
        self.durations: Deque[float]    = deque(maxlen=maxlen)
        self.timestamps: Deque[str]     = deque(maxlen=maxlen)
        self.total_detections: int      = 0
        self.anomaly_count: int         = 0
        self.false_detection_count: int = 0

    def add(self, strength: float, duration_ms: float, ts: str):
        self.strengths.append(strength)
        self.durations.append(duration_ms)
        self.timestamps.append(ts)
        self.total_detections += 1

    @property
    def mean_strength(self) -> float:
        return float(np.mean(self.strengths)) if self.strengths else 0.0

    @property
    def std_strength(self) -> float:
        return float(np.std(self.strengths)) if len(self.strengths) > 1 else 0.0

    @property
    def drift(self) -> float:
        """Relative drift: (recent_mean - baseline_mean) / baseline_mean"""
        if len(self.strengths) < 20:
            return 0.0
        arr = np.array(self.strengths)
        baseline = arr[: len(arr) // 2].mean()
        recent   = arr[len(arr) // 2 :].mean()
        return abs(recent - baseline) / (baseline + 1e-9)


_buffers: Dict[str, SensorBuffer] = {s: SensorBuffer() for s in config.SENSORS}
_start_time = datetime.utcnow()

# ─────────────────────────────────────────────────────────────────────────────
#  ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_anomaly(sensor: str, strength: float) -> bool:
    """Z-score anomaly detection against rolling sensor baseline."""
    buf = _buffers.get(sensor)
    if buf is None or len(buf.strengths) < 10:
        return False
    mean = buf.mean_strength
    std  = buf.std_strength
    if std < 1e-6:
        return False
    z = abs(strength - mean) / std
    if z > config.ANOMALY_Z_SCORE:
        buf.anomaly_count += 1
        logger.warning("Anomaly on %s: strength=%.1f z=%.2f", sensor, strength, z)
        return True
    return False


def is_false_detection(strength: float) -> bool:
    return strength < config.MIN_SIGNAL_STRENGTH


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN INGESTION POINT
# ─────────────────────────────────────────────────────────────────────────────

def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a raw MQTT event with AI flags. Returns the augmented record."""
    sensor     = event.get("sensor", "UNKNOWN")
    strength   = float(event.get("strength", 0))
    duration   = float(event.get("duration_ms", 0))
    ts         = event.get("timestamp", datetime.utcnow().isoformat())

    buf = _buffers.get(sensor, SensorBuffer())
    buf.add(strength, duration, ts)
    _buffers[sensor] = buf

    is_anomaly  = detect_anomaly(sensor, strength)
    is_false    = is_false_detection(strength)
    drift_flag  = buf.drift > config.DRIFT_THRESHOLD
    maint_due   = buf.total_detections % config.MAINTENANCE_CYCLES == 0 \
                  and buf.total_detections > 0

    if is_false:
        buf.false_detection_count += 1

    return {
        "timestamp":       ts,
        "device_id":       event.get("device_id", "ESP32_01"),
        "sensor":          sensor,
        "event_type":      event.get("event", "DETECTION"),
        "signal_strength": int(strength),
        "duration_ms":     int(duration),
        "belt_speed":      float(event.get("belt_speed", 0)),
        "object_id":       event.get("object_id"),
        "is_anomaly":      int(is_anomaly),
        "is_false_det":    int(is_false),
        "drift_flag":      int(drift_flag),
        "maintenance_due": int(maint_due),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  SUMMARY STATISTICS
# ─────────────────────────────────────────────────────────────────────────────

def get_sensor_health() -> List[Dict]:
    out = []
    for sensor, buf in _buffers.items():
        out.append({
            "sensor":            sensor,
            "total_detections":  buf.total_detections,
            "anomaly_count":     buf.anomaly_count,
            "false_detections":  buf.false_detection_count,
            "avg_strength":      round(buf.mean_strength, 1),
            "drift_pct":         round(buf.drift * 100, 1),
            "drift_warning":     buf.drift > config.DRIFT_THRESHOLD,
            "maintenance_due":   buf.total_detections % config.MAINTENANCE_CYCLES == 0
                                 and buf.total_detections > 0,
        })
    return out


def get_uptime() -> str:
    delta = datetime.utcnow() - _start_time
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def compute_dataframe_analytics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute rich statistics from a pandas DataFrame of detections."""
    if df.empty:
        return {}

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    hourly  = df.groupby([df["timestamp"].dt.floor("h"), "sensor"]).size().reset_index(name="count")
    peak_hr = hourly.loc[hourly["count"].idxmax()] if not hourly.empty else None

    detection_rate = len(df) / max(
        (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 60, 1
    )

    return {
        "total":           len(df),
        "by_sensor":       df["sensor"].value_counts().to_dict(),
        "avg_strength":    round(df["signal_strength"].mean(), 1),
        "avg_duration":    round(df["duration_ms"].mean(), 1),
        "avg_speed":       round(df["belt_speed"].mean(), 3),
        "detection_rate":  round(detection_rate, 2),
        "anomaly_count":   int(df["is_anomaly"].sum()),
        "false_det_count": int(df["is_false_det"].sum()),
        "peak_hour":       str(peak_hr["timestamp"]) if peak_hr is not None else "N/A",
    }
