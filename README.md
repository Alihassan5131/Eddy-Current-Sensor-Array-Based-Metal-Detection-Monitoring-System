---

title: ConveyorAI Monitor
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.32.0"
app_file: app.py
pinned: false
license: mit

---

# ⚡ ConveyorAI Monitor
### AI-Enabled Industrial Conveyor Belt Metal Detection & Monitoring System
**Using Eddy Current Sensing and IoT (ESP32 + MQTT)**

---

## 🏗️ System Architecture

```
ESP32 ──[MQTT]──► Broker ──[paho-mqtt]──► Streamlit App ──► SQLite DB
  │                                            │
  └─ Eddy Current Sensors (LEFT / CENTER / RIGHT)     └─ AI Processing
                                                           └─ Analytics
                                                           └─ 3D Vis
```

---

## 🚀 Hugging Face Spaces Deployment

### Step 1 — Create Space
1. Log in to [huggingface.co](https://huggingface.co)
2. New → Space → SDK: **Streamlit** → Python 3.10
3. Name: `conveyorai-monitor`

### Step 2 — Upload Files
Upload these files to the Space:
```
app.py
config.py
database.py
mqtt_handler.py
analytics.py
visualization.py
auth.py
utils.py
requirements.txt
README.md (this file)
```

### Step 3 — Environment Variables (optional)
In Space Settings → Variables:
```
MQTT_BROKER   = broker.hivemq.com
MQTT_PORT     = 1883
MQTT_USERNAME = (leave blank for public broker)
MQTT_PASSWORD = (leave blank for public broker)
DB_PATH       = /tmp/conveyor.db
```

### Step 4 — Launch
Space auto-builds and deploys. Visit your Space URL!

---

## 🔬 Google Colab Testing

```python
# ── Cell 1: Install ─────────────────────────────────────────────
!pip install streamlit paho-mqtt plotly pandas numpy scikit-learn \
             openpyxl fpdf2 streamlit-autorefresh pydeck -q

# ── Cell 2: Upload files ─────────────────────────────────────────
# Use Colab file panel or:
!wget https://your-repo/conveyor_app.zip && unzip conveyor_app.zip

# ── Cell 3: Launch with ngrok ────────────────────────────────────
!pip install pyngrok -q
from pyngrok import ngrok

# Kill any existing tunnels
ngrok.kill()

# Open tunnel on port 8501
public_url = ngrok.connect(8501)
print(f"App URL: {public_url}")

# Run in background
import subprocess
proc = subprocess.Popen(
    ["streamlit", "run", "app.py", "--server.port", "8501"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
print("Streamlit started!")

# ── Cell 4: Run ESP32 simulator ──────────────────────────────────
!python esp32_simulator.py &
```

---

## 📡 MQTT Setup

### Public Broker (zero config)
Default uses `broker.hivemq.com` — no credentials needed.

### Private Broker (production)
```bash
# Install Mosquitto
sudo apt install mosquitto mosquitto-clients

# Start
sudo systemctl start mosquitto

# Test publish
mosquitto_pub -h localhost -t metal_detector/events \
  -m '{"device_id":"ESP32_01","event":"DETECTION","sensor":"LEFT",
       "timestamp":"2026-05-07T12:00:00","strength":87,"duration_ms":12,
       "belt_speed":0.42,"object_id":1001}'
```

### Arduino (ESP32) Sketch Template
```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* ssid     = "YOUR_WIFI";
const char* password = "YOUR_PASS";
const char* mqtt_server = "broker.hivemq.com";

WiFiClient   espClient;
PubSubClient client(espClient);

// Eddy current sensor pins
#define SENSOR_LEFT   34
#define SENSOR_CENTER 35
#define SENSOR_RIGHT  32

int objectId = 1000;

void publishDetection(const char* sensor, int strength) {
  StaticJsonDocument<256> doc;
  doc["device_id"]   = "ESP32_01";
  doc["event"]       = "DETECTION";
  doc["sensor"]      = sensor;
  doc["timestamp"]   = "2026-05-07T12:00:00"; // use NTP
  doc["strength"]    = strength;
  doc["duration_ms"] = 12;
  doc["belt_speed"]  = 0.42;
  doc["object_id"]   = objectId++;

  char buf[256];
  serializeJson(doc, buf);
  client.publish("metal_detector/events", buf);
}

void loop() {
  int left   = analogRead(SENSOR_LEFT)   / 40;
  int center = analogRead(SENSOR_CENTER) / 40;
  int right  = analogRead(SENSOR_RIGHT)  / 40;

  if (left   > 20) publishDetection("LEFT",   left);
  if (center > 20) publishDetection("CENTER", center);
  if (right  > 20) publishDetection("RIGHT",  right);

  delay(10);  // 100 Hz polling
}
```

---

## 🗄️ SQLite Schema

```sql
CREATE TABLE detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,        -- ISO8601
    device_id       TEXT    NOT NULL,
    sensor          TEXT    NOT NULL,        -- LEFT / CENTER / RIGHT
    event_type      TEXT    NOT NULL,        -- DETECTION / STATUS
    signal_strength INTEGER NOT NULL,        -- 0–100
    duration_ms     INTEGER NOT NULL,        -- detection duration
    belt_speed      REAL    NOT NULL,        -- m/s
    object_id       INTEGER,                 -- rolling counter from ESP32
    is_anomaly      INTEGER NOT NULL DEFAULT 0,
    is_false_det    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    DEFAULT (datetime('now'))
);
```

---

## 🔐 Default Credentials

| Role     | Username | Password    |
|----------|----------|-------------|
| Admin    | admin    | admin123    |
| Operator | operator | operator123 |

> **Change these before production deployment!** Edit `config.py → USERS`

---

## 📁 File Structure

```
conveyor_app/
├── app.py              ← Streamlit entry point
├── config.py           ← Central config & env vars
├── database.py         ← SQLite manager (batched WAL writes)
├── mqtt_handler.py     ← Async paho-mqtt client + debounce
├── analytics.py        ← AI: anomaly detection, drift, maintenance
├── visualization.py    ← Plotly 3D belt + all charts
├── auth.py             ← Login page + session management
├── utils.py            ← CSV/Excel/PDF export + formatting
├── esp32_simulator.py  ← Test publisher (mimics real ESP32)
├── requirements.txt
└── README.md
```

---

## ⚡ Features Summary

| Feature | Implementation |
|---------|---------------|
| Real-time MQTT | paho-mqtt, threaded, auto-reconnect |
| 3D Conveyor Belt | Plotly 3D Surface + Scatter3d |
| Anomaly Detection | Z-score rolling baseline per sensor |
| False Detection Filter | Min signal threshold + debounce |
| Drift Monitoring | Rolling mean comparison |
| Predictive Maintenance | Detection cycle counter |
| Export | CSV, Excel (openpyxl), PDF (fpdf2) |
| Authentication | Session-based, role-aware |
| Database | SQLite WAL, batched writes, indexed |
| Auto-refresh | streamlit-autorefresh |
