"""
database.py — SQLite persistence layer with batched, indexed writes
"""

import sqlite3
import threading
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=MEMORY;

CREATE TABLE IF NOT EXISTS detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    device_id       TEXT    NOT NULL DEFAULT 'ESP32_01',
    sensor          TEXT    NOT NULL,
    event_type      TEXT    NOT NULL DEFAULT 'DETECTION',
    signal_strength INTEGER NOT NULL,
    duration_ms     INTEGER NOT NULL,
    belt_speed      REAL    NOT NULL,
    object_id       INTEGER,
    is_anomaly      INTEGER NOT NULL DEFAULT 0,
    is_false_det    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp);
CREATE INDEX IF NOT EXISTS idx_detections_sensor     ON detections(sensor);
CREATE INDEX IF NOT EXISTS idx_detections_object_id  ON detections(object_id);

CREATE TABLE IF NOT EXISTS system_status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    topic       TEXT NOT NULL,
    payload     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_health (
    sensor          TEXT    PRIMARY KEY,
    total_detections INTEGER DEFAULT 0,
    last_seen       TEXT,
    avg_strength    REAL DEFAULT 0,
    drift_flag      INTEGER DEFAULT 0,
    maintenance_due INTEGER DEFAULT 0
);

INSERT OR IGNORE INTO sensor_health(sensor) VALUES ('LEFT'), ('CENTER'), ('RIGHT');
"""

# ─────────────────────────────────────────────────────────────────────────────
#  CONNECTION MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    """Thread-safe SQLite manager with batched write buffer."""

    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path   = db_path
        self._lock     = threading.Lock()
        self._buffer: List[Dict] = []
        self._last_flush = time.time()
        self._init_db()
        self._start_flush_thread()

    # ── Initialise ────────────────────────────────────────────────────────────
    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(DDL)
        logger.info("Database initialised at %s", self.db_path)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("DB error: %s", exc)
            raise
        finally:
            conn.close()

    # ── Buffered write ────────────────────────────────────────────────────────
    def buffer_detection(self, record: Dict[str, Any]):
        """Add a detection record to the write buffer."""
        with self._lock:
            self._buffer.append(record)
            if (
                len(self._buffer) >= config.DB_WRITE_BATCH_SIZE
                or time.time() - self._last_flush >= config.DB_WRITE_INTERVAL
            ):
                self._flush()

    def _flush(self):
        """Flush buffer to disk (must be called under self._lock)."""
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        self._last_flush = time.time()
        try:
            with self._connect() as conn:
                conn.executemany(
                    """INSERT INTO detections
                       (timestamp, device_id, sensor, event_type,
                        signal_strength, duration_ms, belt_speed,
                        object_id, is_anomaly, is_false_det)
                       VALUES (:timestamp, :device_id, :sensor, :event_type,
                               :signal_strength, :duration_ms, :belt_speed,
                               :object_id, :is_anomaly, :is_false_det)""",
                    batch,
                )
                # Update sensor health
                for rec in batch:
                    conn.execute(
                        """UPDATE sensor_health
                           SET total_detections = total_detections + 1,
                               last_seen        = :ts,
                               avg_strength     = (avg_strength * (total_detections) + :s)
                                                   / (total_detections + 1),
                               drift_flag       = :df,
                               maintenance_due  = :md
                           WHERE sensor = :sensor""",
                        {
                            "ts":     rec["timestamp"],
                            "s":      rec["signal_strength"],
                            "df":     rec.get("drift_flag", 0),
                            "md":     rec.get("maintenance_due", 0),
                            "sensor": rec["sensor"],
                        },
                    )
            logger.debug("Flushed %d records to DB", len(batch))
        except Exception as exc:
            logger.error("Flush failed: %s", exc)

    def force_flush(self):
        with self._lock:
            self._flush()

    def _start_flush_thread(self):
        def _worker():
            while True:
                time.sleep(config.DB_WRITE_INTERVAL)
                with self._lock:
                    self._flush()
        t = threading.Thread(target=_worker, daemon=True, name="db-flush")
        t.start()

    # ── Queries ───────────────────────────────────────────────────────────────
    def get_recent_detections(self, limit: int = config.MAX_LOG_ROWS) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_kpi_summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM detections WHERE is_false_det=0"
            ).scalar() if hasattr(conn, "scalar") else \
                conn.execute("SELECT COUNT(*) FROM detections WHERE is_false_det=0").fetchone()[0]

            per_sensor = {}
            for s in config.SENSORS:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM detections WHERE sensor=? AND is_false_det=0",
                    (s,)
                ).fetchone()[0]
                per_sensor[s] = cnt

            avg_speed = conn.execute(
                "SELECT AVG(belt_speed) FROM detections"
            ).fetchone()[0] or 0

            last_hour = conn.execute(
                """SELECT COUNT(*) FROM detections
                   WHERE is_false_det=0
                   AND timestamp >= datetime('now','-1 hour')"""
            ).fetchone()[0]

            health_rows = conn.execute("SELECT * FROM sensor_health").fetchall()
        return {
            "total":        total,
            "per_sensor":   per_sensor,
            "avg_speed":    round(avg_speed, 3),
            "last_hour":    last_hour,
            "sensor_health": [dict(r) for r in health_rows],
        }

    def get_timeline_data(self, hours: int = 24) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT timestamp, sensor, signal_strength, belt_speed, object_id
                   FROM detections
                   WHERE is_false_det=0
                     AND timestamp >= datetime('now', ? || ' hours')
                   ORDER BY timestamp""",
                (f"-{hours}",)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_hourly_stats(self, days: int = 7) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT strftime('%Y-%m-%d %H:00', timestamp) AS hour,
                          sensor,
                          COUNT(*) AS detections,
                          AVG(signal_strength) AS avg_strength,
                          AVG(belt_speed) AS avg_speed
                   FROM detections
                   WHERE is_false_det=0
                     AND timestamp >= datetime('now', ? || ' days')
                   GROUP BY hour, sensor
                   ORDER BY hour""",
                (f"-{days}",)
            ).fetchall()
        return [dict(r) for r in rows]

    def log_status(self, topic: str, payload: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO system_status(timestamp,topic,payload) VALUES(?,?,?)",
                (datetime.utcnow().isoformat(), topic, payload)
            )

    def get_db_stats(self) -> Dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
            size_kb = 0
            try:
                import os
                size_kb = os.path.getsize(self.db_path) // 1024
            except Exception:
                pass
        return {"total_records": total, "size_kb": size_kb}


# ── Module-level singleton ────────────────────────────────────────────────────
db = DatabaseManager()
