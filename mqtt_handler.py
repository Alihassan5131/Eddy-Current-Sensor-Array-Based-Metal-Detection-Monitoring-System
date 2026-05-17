"""
mqtt_handler.py — Async MQTT client with auto-reconnect, event queue, and debounce
"""

import json
import logging
import queue
import threading
import time
from datetime import datetime
from typing import Callable, Dict, Any, Optional

import paho.mqtt.client as mqtt

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  SHARED STATE  (read by Streamlit from main thread)
# ─────────────────────────────────────────────────────────────────────────────

class MQTTState:
    connected: bool         = False
    last_message_ts: Optional[str] = None
    broker: str             = config.MQTT_BROKER
    rx_count: int           = 0
    error_count: int        = 0
    reconnect_count: int    = 0


state = MQTTState()
event_queue: queue.Queue = queue.Queue(maxsize=10_000)   # high-throughput buffer

# ─────────────────────────────────────────────────────────────────────────────
#  MQTT CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class MQTTHandler:
    """Wraps paho-mqtt with thread-safe state and debounce logic."""

    def __init__(self, on_detection: Optional[Callable[[Dict], None]] = None):
        self._on_detection = on_detection   # optional callback (besides queue)
        self._debounce: Dict[str, float] = {}  # sensor → last event epoch (ms)
        self._client: Optional[mqtt.Client] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ── Paho callbacks ────────────────────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            state.connected = True
            logger.info("MQTT connected to %s", config.MQTT_BROKER)
            for topic in config.MQTT_TOPICS:
                client.subscribe(topic)
                logger.info("Subscribed: %s", topic)
        else:
            logger.warning("MQTT connect failed rc=%d", rc)
            state.connected = False

    def _on_disconnect(self, client, userdata, rc):
        state.connected = False
        state.reconnect_count += 1
        logger.warning("MQTT disconnected rc=%d (reconnect #%d)", rc, state.reconnect_count)

    def _on_message(self, client, userdata, msg):
        try:
            raw = msg.payload.decode("utf-8")
            data: Dict[str, Any] = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            state.error_count += 1
            logger.error("Bad packet on %s: %s", msg.topic, exc)
            return

        state.rx_count += 1
        state.last_message_ts = datetime.utcnow().isoformat()

        if msg.topic == "metal_detector/events":
            self._handle_detection(data)
        elif msg.topic == "metal_detector/status":
            self._handle_status(data)

    # ── Processing ────────────────────────────────────────────────────────────
    def _handle_detection(self, data: Dict):
        sensor = data.get("sensor", "UNKNOWN")
        now_ms = time.time() * 1000

        # debounce: skip if too fast from same sensor
        last = self._debounce.get(sensor, 0)
        if now_ms - last < config.DEBOUNCE_MS:
            return
        self._debounce[sensor] = now_ms

        # basic validation
        strength = int(data.get("strength", 0))
        if strength < config.MIN_SIGNAL_STRENGTH:
            data["is_false_det"] = 1
        else:
            data["is_false_det"] = 0

        try:
            event_queue.put_nowait(data)
        except queue.Full:
            logger.warning("Event queue full — dropping oldest")
            try:
                event_queue.get_nowait()
                event_queue.put_nowait(data)
            except queue.Empty:
                pass

        if self._on_detection:
            try:
                self._on_detection(data)
            except Exception as exc:
                logger.error("on_detection callback error: %s", exc)

    def _handle_status(self, data: Dict):
        # store raw status for logging; handled elsewhere
        pass

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="mqtt-handler"
        )
        self._thread.start()
        logger.info("MQTT handler thread started")

    def stop(self):
        self._stop_event.set()
        if self._client:
            self._client.disconnect()

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self._client = mqtt.Client(client_id=config.MQTT_CLIENT_ID)
                self._client.on_connect    = self._on_connect
                self._client.on_disconnect = self._on_disconnect
                self._client.on_message    = self._on_message

                if config.MQTT_USERNAME:
                    self._client.username_pw_set(
                        config.MQTT_USERNAME, config.MQTT_PASSWORD
                    )

                self._client.connect(
                    config.MQTT_BROKER,
                    config.MQTT_PORT,
                    config.MQTT_KEEPALIVE
                )
                self._client.loop_forever()
            except Exception as exc:
                logger.error("MQTT loop error: %s", exc)
                state.connected = False
            finally:
                if not self._stop_event.is_set():
                    logger.info(
                        "Reconnecting in %ds…", config.MQTT_RECONNECT_DELAY
                    )
                    time.sleep(config.MQTT_RECONNECT_DELAY)

    def drain_queue(self, max_items: int = 200) -> list:
        """Drain up to max_items from the queue. Called by Streamlit."""
        items = []
        for _ in range(max_items):
            try:
                items.append(event_queue.get_nowait())
            except queue.Empty:
                break
        return items


# Module-level singleton — started once per process
_handler: Optional[MQTTHandler] = None


def get_handler() -> MQTTHandler:
    global _handler
    if _handler is None:
        _handler = MQTTHandler()
        _handler.start()
    return _handler
