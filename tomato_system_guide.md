# Tomato Quality Detection System - Architecture Guide

## 1. Arduino vs ESP32 Recommendation: **USE ESP32**

### Why ESP32 is Better for Your Use Case:

| Feature | Arduino Uno | ESP32 |
|---------|-----------|-------|
| **PWM Pins** | 6 (limited servo control) | 16+ (perfect for 2-3 servos) | 
| **IR Sensor Support** | ✓ Works | ✓ Better, more reliable |
| **Servo Control** | Basic (8-bit resolution) | Advanced (16-bit PWM) |
| **Multitasking** | Single-core, sequential | Dual-core (parallel IR detection + servo control) |
| **WiFi/Bluetooth** | ✗ Need additional modules | ✓ Built-in |
| **Power Efficiency** | Better for simple tasks | Better for complex IoT |
| **Serial Communication** | Via USB | Via USB or native UART |

**Source:** [web:133][web:134][web:136]

**Advantages for tomato system:**
- Parallel processing: IR detection while servo operating
- More GPIO pins for future expansions (additional sensors)
- Better servo control precision via 16-bit PWM
- Can handle IR sensor + 3 servos simultaneously without blocking

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                     RASPBERRY PI                     │
│  (Ubuntu/Raspberry Pi OS)                            │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │         rasp.py (Main Controller)             │  │
│  │  - Serial communication with ESP32           │  │
│  │  - Camera capture trigger                    │  │
│  │  - MQTT publisher                            │  │
│  └──────────────────────────────────────────────┘  │
│         ↓                                            │
│  ┌──────────────────────────────────────────────┐  │
│  │         Modules (rasp/)                       │  │
│  │  - arduino_reader.py (serial data)           │  │
│  │  - camera_handler.py (Logitech C270)         │  │
│  │  - model_loader.py (YOLO from HF)            │  │
│  │  - preprocess.py (1280x720 → 640x640)        │  │
│  │  - inference.py (detect tomato class)        │  │
│  │  - mqtt_publisher.py (send predictions)      │  │
│  └──────────────────────────────────────────────┘  │
│         ↓ (MQTT)                                    │
└─────────────────────────────────────────────────────┘
         ↓
    MQTT Broker (localhost:1883)
         ↓
┌─────────────────────────────────────────────────────┐
│                   WINDOWS PC                         │
│  (Server - Supabase + Dashboard)                    │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │         server.py (Main Server)               │  │
│  │  - MQTT subscriber                           │  │
│  │  - Supabase connector                        │  │
│  │  - Data logging                              │  │
│  └──────────────────────────────────────────────┘  │
│         ↓                                            │
│  ┌──────────────────────────────────────────────┐  │
│  │         Modules (server/)                     │  │
│  │  - mqtt_listener.py (receive predictions)    │  │
│  │  - supabase_handler.py (PostgreSQL insert)   │  │
│  │  - dashboard.py (Streamlit dashboard)        │  │
│  └──────────────────────────────────────────────┘  │
│         ↓ (Supabase REST API)                       │
└─────────────────────────────────────────────────────┘
         ↓
    SUPABASE CLOUD
    (PostgreSQL + Storage)
         ↓
    Deployed on HF Spaces (Streamlit Dashboard)
         ↓
    Hugging Face Model Hub (YOLO weights)
```

---

## 3. File Structure

```
tomato-detection/
├── rasp/                          # Raspberry Pi side
│   ├── rasp.py                    # Main entry point
│   ├── arduino_reader.py          # Serial communication (IR + servo feedback)
│   ├── camera_handler.py          # Logitech C270 capture
│   ├── model_loader.py            # Load YOLO from HF (huggingface_hub)
│   ├── preprocess.py              # Resize 1280x720 → 640x640
│   ├── inference.py               # Run YOLO detection
│   ├── mqtt_publisher.py          # Send results (class, id, timestamp)
│   ├── config.py                  # Settings (MQTT broker, model name)
│   └── requirements_rasp.txt      # Python deps
│
├── server/                        # Windows/Server side
│   ├── server.py                  # Main entry point
│   ├── mqtt_listener.py           # Subscribe to MQTT
│   ├── supabase_handler.py        # PostgreSQL operations
│   ├── dashboard.py               # Streamlit UI
│   ├── config.py                  # API keys, DB config
│   └── requirements_server.txt    # Python deps
│
├── arduino/                       # ESP32 code (Arduino IDE)
│   ├── esp32_main.ino             # IR sensor + servo control
│   ├── servo_control.h            # Servo library wrapper
│   ├── ir_sensor.h                # IR sensor handler
│   └── README.md                  # Setup instructions
│
├── models/                        # YOLO model storage (optional)
│   └── tomato_model.pt            # Or download from HF
│
└── README.md                      # Overall project docs
```

---

## 4. Model Deployment Strategy: **Local Loading from HF**

### Comparison:

| Approach | Pros | Cons | Recommendation |
|----------|------|------|-----------------|
| **Load model directly from HF on Pi** | No re-packaging, always fresh, uses HF Hub library | First load slow (~500MB download) | ✓ **Use this** |
| **Package model in repo** | Faster startup | Large file in git (900MB+) | ✗ Not for repo |
| **Download model on boot** | Flexibility | Network dependency on Pi | ✓ Acceptable fallback |

**Recommended Approach:**

```python
# model_loader.py
from huggingface_hub import hf_hub_download
import torch

def load_tomato_model(model_name="your-username/tomato-yolo"):
    """
    Load YOLO model from Hugging Face Hub
    model_name: "your-username/tomato-yolo" (in HF)
    """
    try:
        model_path = hf_hub_download(
            repo_id=model_name, 
            filename="best.pt",  # Your trained model
            cache_dir="/tmp/hf_models"  # Cache locally
        )
        model = torch.hub.load('ultralytics/yolov8', 'custom', path=model_path)
        print(f"✓ Model loaded from HF: {model_path}")
        return model
    except Exception as e:
        print(f"✗ Failed to load from HF: {e}")
        # Fallback: load from local if cached
        return None

# On Pi startup: downloads once, then uses cached version
```

**Why:**
- Pi only downloads model first time (~10 min on WiFi, then cached)
- Updates easy: just re-download from HF if you retrain
- No large files in git repo
- Supabase Cloud (PostgreSQL) stores metadata/predictions, not models

**Source:** [web:138][web:142]

---

## 5. Image Processing: Resize vs Let Model Handle

### Recommendation: **Pre-resize to 640x640**

| Approach | Latency | Quality | Memory | Recommendation |
|----------|---------|---------|--------|-----------------|
| **Send 1280x720 raw** | ~500ms (model resizes inside) | Slightly better | Higher | ✗ Slower on Pi |
| **Pre-resize to 640x640** | ~200ms (done before inference) | Slight quality loss | Efficient | ✓ **Use this** |

**Code:**

```python
# preprocess.py
import cv2

def preprocess_tomato_image(frame, target_size=640):
    """
    Resize Logitech C270 1280x720 to YOLO input size
    """
    # YOLOv8 accepts: 320x320, 416x416, 640x640, 1280x1280
    resized = cv2.resize(frame, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
    normalized = resized.astype('float32') / 255.0
    return normalized
```

**Rationale:**
- Pi CPU limited; pre-processing saves ~300ms per inference
- 640x640 is sweet spot: fast enough, accuracy sufficient for tomato classification
- YOLO designed for 640x640 (Ultralytics default)

---

## 6. Tomato Classification Classes

Define in config or database:

```python
# config.py
TOMATO_CLASSES = {
    0: "ripe",
    1: "unripe",
    2: "damaged",
    3: "old"
}

# MQTT payload example:
{
    "class": "ripe",
    "confidence": 0.95,
    "tomato_id": "tm_20251130_154530_001",
    "timestamp": "2025-11-30T15:45:30Z",
    "servo_action": "gate_to_box_1"  # Which box to direct servo
}
```

---

## 7. Arduino/ESP32 to Raspberry Pi Communication

### Recommended: Serial (USB) + TTY2MQTT Bridge (Optional)

**Simple Approach (Direct Serial):**

```python
# arduino_reader.py (on Pi)
import serial
import json

class ArduinoReader:
    def __init__(self, port='/dev/ttyUSB0', baud=115200):
        self.ser = serial.Serial(port, baud, timeout=1)
    
    def read_ir_signal(self):
        """Blocks until tomato detected"""
        if self.ser.in_waiting:
            line = self.ser.readline().decode('utf-8').strip()
            try:
                data = json.loads(line)
                return data  # {"ir_detected": true, "timestamp": "..."}
            except:
                return None
    
    def send_servo_command(self, servo_id, angle):
        """Tell ESP32 to move servo"""
        cmd = json.dumps({"servo": servo_id, "angle": angle})
        self.ser.write(cmd.encode() + b'\n')
```

**ESP32 Code (Arduino IDE):**

```cpp
// esp32_main.ino
#include <ArduinoJson.h>

const int IR_PIN = 25;         // IR sensor input
const int SERVO_PINS[] = {12, 14, 27};  // 3 servos

void setup() {
    Serial.begin(115200);
    pinMode(IR_PIN, INPUT);
}

void loop() {
    // Check IR sensor
    if (digitalRead(IR_PIN) == LOW) {  // Tomato detected
        delay(50);  // Debounce
        if (digitalRead(IR_PIN) == LOW) {
            StaticJsonDocument<128> doc;
            doc["ir_detected"] = true;
            doc["timestamp"] = millis();
            serializeJson(doc, Serial);
            Serial.println();
            delay(500);
        }
    }
    
    // Listen for servo commands from Pi
    if (Serial.available()) {
        StaticJsonDocument<128> doc;
        deserializeJson(doc, Serial);
        int servo_id = doc["servo"];
        int angle = doc["angle"];
        moveServo(servo_id, angle);
    }
}

void moveServo(int id, int angle) {
    // Use ESP32Servo library or PWM
    // PWM control for servo 0-180 degrees
}
```

**Source:** [web:139][web:137]

---

## 8. Streamlit Dashboard on HF Spaces

### Deployment Steps:

1. **Create Streamlit app (server/dashboard.py):**

```python
# dashboard.py
import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Tomato Detection", layout="wide")

# Supabase connection
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🍅 Tomato Quality Detection Dashboard")

# Fetch recent predictions
response = supabase.table("predictions").select("*").order("timestamp", desc=True).limit(100).execute()
df = pd.DataFrame(response.data)

st.dataframe(df, use_container_width=True)

# Charts
col1, col2 = st.columns(2)
with col1:
    class_counts = df['class'].value_counts()
    st.bar_chart(class_counts)
with col2:
    st.metric("Total Scanned", len(df))
```

2. **Push to HF Spaces:**
   - Create space at huggingface.co/spaces
   - Select **Streamlit** SDK
   - Add `requirements.txt` + `secrets.toml`
   - Git push or upload files

3. **Configure secrets (HF Spaces UI):**
   - Add SUPABASE_URL and SUPABASE_KEY in Space settings

**Source:** [web:140]

---

## 9. Supabase PostgreSQL Schema

```sql
-- Table: predictions
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tomato_id VARCHAR(50) UNIQUE NOT NULL,
    class VARCHAR(20) NOT NULL,  -- ripe, unripe, damaged, old
    confidence FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    servo_action VARCHAR(50),
    image_url VARCHAR(500)  -- URL in Supabase Storage
);

-- Table: servo_log
CREATE TABLE servo_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    servo_id INT,
    angle INT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

---

## 10. Setup Checklist

### On Raspberry Pi:
- [ ] Install Python 3, venv
- [ ] Install: `pip install opencv-python paho-mqtt supabase huggingface-hub torch ultralytics`
- [ ] Clone repo & create `config.py` with MQTT broker IP, Supabase credentials
- [ ] Connect Logitech C270 USB camera
- [ ] Connect ESP32 via USB serial

### On Windows:
- [ ] Install Python 3, Node.js
- [ ] Install: `pip install paho-mqtt supabase streamlit pandas`
- [ ] Run MQTT broker locally (mosquitto) OR use cloud broker
- [ ] Run `server.py` to start listening to Pi
- [ ] Deploy dashboard to HF Spaces

### On ESP32:
- [ ] Install Arduino IDE + ESP32 board
- [ ] Connect IR sensor to GPIO 25
- [ ] Connect 3 servos to GPIO 12, 14, 27 (PWM)
- [ ] Upload `esp32_main.ino`
- [ ] Test with Serial Monitor

### On Hugging Face:
- [ ] Train/fine-tune YOLO on tomato dataset
- [ ] Upload model to HF as private repo (your-username/tomato-yolo)
- [ ] Create Spaces for dashboard (connect to Supabase)

---

## 11. Recommended Tech Stack Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| Edge Device | ESP32 | IR + 3 servos, dual-core, WiFi optional |
| Processing | Raspberry Pi 3B+ | Camera + YOLO inference + MQTT |
| Camera | Logitech C270 | USB plug-and-play, 1280x720 |
| ML Model | YOLOv8 (HF) | Fast, accurate, easy to deploy |
| Backend DB | Supabase (PostgreSQL) | Free tier, no Docker, API-ready |
| Dashboard | Streamlit on HF Spaces | Free hosting, no DevOps |
| Communication | MQTT (mosquitto) | Light, reliable, pub-sub pattern |
| Serial Link | USB + JSON | Simple, robust, no extra library |

---

## 12. Next Steps

1. **Train YOLO model** on tomato images (Roboflow or custom dataset)
2. **Upload to HF Hub** as `your-username/tomato-yolo`
3. **Implement rasp.py** flow: IR trigger → camera → preprocess → inference → MQTT
4. **Implement server.py** flow: MQTT listen → Supabase insert → live dashboard
5. **Upload ESP32 code** and test servo movement
6. **Deploy dashboard** to HF Spaces with live Supabase connection

All code written in Python (except Arduino IDE) for consistency with your ML background.
