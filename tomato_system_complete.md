# Tomato Detection System - Complete Setup Guide

## Overview

Full-stack tomato quality detection system using YOLO, MQTT, and cloud deployment:

- **Edge Device (Raspberry Pi):** Captures video → runs YOLO inference → publishes predictions via MQTT
- **Middleware (Windows Server):** Listens to MQTT → forwards predictions to cloud API via HTTP
- **Cloud (HF Spaces):** Receives data → stores in Supabase PostgreSQL → serves API + Dashboard

---

## Architecture Diagram

```
┌──────────────────┐
│   ESP32          │
│ IR Sensor + 3x   │
│ MG996R Servos    │
└────────┬─────────┘
         │ Serial
         ↓
┌──────────────────────────────────┐
│   RASPBERRY PI 3B+               │
│ (Ubuntu/Raspberry Pi OS)         │
│                                  │
│  rasp.py:                        │
│  - Read IR from ESP32            │
│  - Capture frame (C270 camera)   │
│  - YOLO inference                │
│  - MQTT publish predictions      │
└────────┬─────────────────────────┘
         │ MQTT
         │ (localhost:1883)
         ↓
┌──────────────────────────────────┐
│   WINDOWS SERVER / LOCAL PC      │
│                                  │
│  server.py:                      │
│  - MQTT listener                 │
│  - HTTP POST to HF Spaces API    │
└────────┬─────────────────────────┘
         │ HTTPS
         ↓
┌──────────────────────────────────┐
│   HUGGING FACE SPACES (Cloud)    │
│                                  │
│  app.py (Flask + Streamlit):     │
│  - Receive predictions via API   │
│  - Insert to Supabase            │
│  - Dashboard visualization       │
└────────┬─────────────────────────┘
         │ REST API
         ↓
┌──────────────────────────────────┐
│   SUPABASE CLOUD (PostgreSQL)    │
│                                  │
│  predictions table:              │
│  - tomato_id, timestamp          │
│  - class, confidence, etc.       │
└──────────────────────────────────┘
```

---

## File Structure

```
tomato-detection/
├── rasp/                          # Raspberry Pi side
│   ├── main.py                    # Main entry point
│   ├── model_loader.py            # Load YOLO (pre-trained or HF)
│   ├── camera_handler.py          # Logitech C270 camera
│   ├── arduino_reader.py          # Serial communication with ESP32
│   ├── preprocess.py              # Image resizing & normalization
│   ├── inference.py               # YOLO inference
│   ├── mqtt_publisher.py          # MQTT client
│   ├── config.py                  # Configuration (settings)
│   ├── requirements_rasp.txt      # Python dependencies
│   └── .env                       # Secrets (HF_TOKEN, MQTT broker)
│
├── server/                        # Windows Server side
│   ├── main.py                    # MQTT listener → HTTP forwarder
│   ├── requirements_server.txt    # Python dependencies
│   └── .env                       # Secrets (API endpoint)
│
├── hf-spaces/                     # Hugging Face Spaces deployment
│   ├── app.py                     # Flask API + Streamlit Dashboard
│   ├── Dockerfile                 # Docker configuration
│   ├── requirements.txt           # Python dependencies
│   └── .streamlit/secrets.toml    # Supabase credentials
│
└── arduino/                       # Arduino IDE (optional)
    ├── main.ino                   # IR sensor + servo control
    └── README.md                  # Setup instructions

```

---

## Part 1: Raspberry Pi Setup (rasp/)

### 1.1 requirements_rasp.txt

```
# Core ML/Vision
opencv-python==4.8.1.78
torch==2.0.1
torchvision==0.15.2
ultralytics==8.0.195

# Model Hub
huggingface-hub==0.19.4

# Data Processing
numpy==1.24.3
Pillow==10.0.0
scipy==1.11.4

# Communication
paho-mqtt==1.6.1
requests==2.31.0
pyserial==3.5

# Configuration
python-dotenv==1.0.0
pyyaml==6.0.1
```

### 1.2 .env (Raspberry Pi)

```
# .env - DO NOT COMMIT TO GIT
MQTT_BROKER=localhost
MQTT_PORT=1883
HF_TOKEN=hf_xxxxxxxxxxxxx
```

### 1.3 config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

# MQTT Configuration
MQTT_CONFIG = {
    "broker_host": os.getenv("MQTT_BROKER", "localhost"),
    "broker_port": int(os.getenv("MQTT_PORT", 1883)),
}

# Tomato Classes
TOMATO_CLASSES = {
    0: "ripe",
    1: "unripe",
    2: "damaged",
    3: "old"
}

# Servo Mapping (class -> servo action)
SERVO_ACTIONS = {
    0: {"servo": 1, "angle": 45},   # Ripe → box 1
    1: {"servo": 1, "angle": 90},   # Unripe → box 2
    2: {"servo": 1, "angle": 135},  # Damaged → box 3
    3: {"servo": 1, "angle": 180},  # Old → reject
}

# Camera Settings
CAMERA_CONFIG = {
    "device": 0,
    "width": 1280,
    "height": 720,
    "fps": 30
}

# Model Settings - FLEXIBLE FOR TESTING & PRODUCTION
MODEL_CONFIG = {
    # TESTING: Use pre-trained nano
    "model_name": "yolov8n",
    "use_huggingface": False,
    
    # PRODUCTION: Switch to custom fine-tuned
    # "model_name": "your-username/tomato-yolo",
    # "use_huggingface": True,
    
    "target_size": 640,
    "inference_method": "single",
}
```

### 1.4 Setup Instructions (Pi)

```bash
# On Raspberry Pi
cd rasp/
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_rasp.txt

# Create .env with your settings
cp .env.example .env
nano .env  # Edit with your MQTT broker and HF token

# Install mosquitto (MQTT broker)
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto

# Run the system
python rasp.py
```

---

## Part 2: Windows Server Setup (server/)

### 2.1 requirements_server.txt

```
# Communication
paho-mqtt==1.6.1
requests==2.31.0

# Configuration
python-dotenv==1.0.0

# Data (optional, for local logging)
pandas==2.1.3
```

### 2.2 .env (Windows Server)

```
# .env - DO NOT COMMIT TO GIT
# Your HF Spaces API endpoint
API_ENDPOINT=https://your-username-tomato-detection.hf.space/api/insert_prediction
```

### 2.3 server.py

```python
import paho.mqtt.client as mqtt
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class MQTTListener:
    def __init__(self, broker_host, api_endpoint):
        """
        Args:
            broker_host (str): MQTT broker address (e.g., "192.168.1.100" or "localhost")
            api_endpoint (str): HF Spaces API endpoint
        """
        self.broker_host = broker_host
        self.api_endpoint = api_endpoint
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(f"✓ Connected to MQTT broker {self.broker_host}")
            self.client.subscribe("tomato/predictions")
            print("✓ Subscribed to tomato/predictions")
        else:
            print(f"✗ Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected"""
        if rc != 0:
            print(f"⚠️  Unexpected disconnection. Reconnecting...")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Parse MQTT payload
            payload = json.loads(msg.payload.decode())
            print(f"\n📨 Received: {payload['tomato_id']}")
            print(f"   Class: {payload['class_name']} ({payload['confidence']:.2%})")
            
            # Forward to HF Spaces API
            self.forward_to_api(payload)
        
        except json.JSONDecodeError:
            print(f"✗ Invalid JSON received: {msg.payload}")
        except Exception as e:
            print(f"✗ Error processing message: {e}")
    
    def forward_to_api(self, prediction_data):
        """Send prediction to HF Spaces API"""
        try:
            response = requests.post(
                self.api_endpoint,
                json=prediction_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 201:
                result = response.json()
                print(f"✓ Saved to database: {result.get('message', 'OK')}")
            else:
                print(f"✗ API error ({response.status_code}): {response.text}")
        
        except requests.exceptions.Timeout:
            print(f"⚠️  API timeout - retrying...")
        except requests.exceptions.ConnectionError:
            print(f"⚠️  Connection error - check API endpoint")
        except Exception as e:
            print(f"✗ Error forwarding to API: {e}")
    
    def start(self):
        """Start listening to MQTT"""
        try:
            self.client.connect(self.broker_host, 1883, 60)
            print("🚀 Starting MQTT listener...")
            self.client.loop_forever()
        except Exception as e:
            print(f"✗ Failed to connect: {e}")

if __name__ == "__main__":
    BROKER_HOST = os.getenv("MQTT_BROKER", "localhost")
    API_ENDPOINT = os.getenv("API_ENDPOINT")
    
    if not API_ENDPOINT:
        print("✗ Error: API_ENDPOINT not set in .env")
        exit(1)
    
    print(f"🍅 Tomato Detection MQTT Listener")
    print(f"   MQTT Broker: {BROKER_HOST}:1883")
    print(f"   API Endpoint: {API_ENDPOINT}\n")
    
    listener = MQTTListener(BROKER_HOST, API_ENDPOINT)
    listener.start()
```

### 2.4 Setup Instructions (Server)

```bash
# On Windows Server / Local PC
cd server/
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements_server.txt

# Create .env
copy .env.example .env
# Edit .env with your HF Spaces API endpoint

# Run
python server.py
```

---

## Part 3: Hugging Face Spaces Setup (hf-spaces/)

### 3.1 Create HF Spaces

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Fill:
   - **Space name:** `tomato-detection`
   - **License:** MIT
   - **Space SDK:** Docker
4. Click "Create space"

### 3.2 requirements.txt

```
streamlit==1.28.1
flask==3.0.0
pandas==2.1.3
supabase==2.0.3
requests==2.31.0
python-dotenv==1.0.0
pyyaml==6.0.1
```

### 3.3 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

# Create Streamlit config
RUN mkdir -p ~/.streamlit
RUN echo "[server]\nheadless = true\nport = 7860" > ~/.streamlit/config.toml

# Run Flask (background) + Streamlit (foreground)
CMD ["sh", "-c", "flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 & streamlit run app.py --server.port=7860 --server.address=0.0.0.0"]
```

### 3.4 app.py (Flask API + Streamlit Dashboard)

```python
# app.py
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import os
import sys
from flask import Flask, request, jsonify
import threading

# ============ CONFIGURATION ============
st.set_page_config(page_title="🍅 Tomato Detection", layout="wide")

# Initialize Supabase from Streamlit secrets
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error loading Supabase credentials: {e}")
    supabase = None

# ============ FLASK API ============
app = Flask(__name__)

@app.route("/api/insert_prediction", methods=["POST"])
def insert_prediction():
    """
    API endpoint to insert predictions
    
    Expected JSON:
    {
        "tomato_id": "tm_20251130_154530_001",
        "timestamp": "2025-11-30T15:45:30.123456Z",
        "class": 0,
        "class_name": "ripe",
        "confidence": 0.9542,
        "method": "single",
        "servo_action": "gate_to_box_1"
    }
    """
    if not supabase:
        return jsonify({"error": "Database not initialized"}), 500
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ["tomato_id", "timestamp", "class", "class_name", "confidence"]
        if not all(field in data for field in required):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Insert to Supabase
        response = supabase.table("predictions").insert([data]).execute()
        
        return jsonify({
            "status": "success",
            "message": f"Inserted {data['tomato_id']}",
            "data": response.data[0] if response.data else None
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_recent", methods=["GET"])
def get_recent():
    """Get recent predictions"""
    if not supabase:
        return jsonify({"error": "Database not initialized"}), 500
    
    try:
        limit = request.args.get("limit", 100, type=int)
        response = supabase.table("predictions").select("*").order(
            "timestamp", desc=True
        ).limit(limit).execute()
        
        return jsonify({
            "status": "success",
            "count": len(response.data),
            "data": response.data
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get statistics"""
    if not supabase:
        return jsonify({"error": "Database not initialized"}), 500
    
    try:
        response = supabase.table("predictions").select("class_name").execute()
        class_counts = {}
        for row in response.data:
            class_name = row["class_name"]
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        return jsonify({
            "status": "success",
            "total": len(response.data),
            "class_counts": class_counts
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run Flask in background
def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

threading.Thread(target=run_flask, daemon=True).start()

# ============ STREAMLIT DASHBOARD ============
st.title("🍅 Tomato Quality Detection Dashboard")

# Sidebar
with st.sidebar:
    st.subheader("System Info")
    st.write("**Status:** 🟢 Online")
    st.write("**API:** Flask (port 5000)")
    st.write("**Database:** Supabase PostgreSQL")

# Main metrics
if supabase:
    try:
        all_data = supabase.table("predictions").select("*").execute()
        data = all_data.data
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Scanned", len(data))
        
        with col2:
            ripe = len([d for d in data if d["class_name"] == "ripe"])
            st.metric("🟢 Ripe", ripe)
        
        with col3:
            damaged = len([d for d in data if d["class_name"] == "damaged"])
            st.metric("🔴 Damaged", damaged)
        
        with col4:
            unripe = len([d for d in data if d["class_name"] == "unripe"])
            st.metric("🟡 Unripe", unripe)
        
        # Charts
        st.subheader("Distribution")
        if data:
            class_names = [d["class_name"] for d in data]
            class_counts = pd.Series(class_names).value_counts()
            st.bar_chart(class_counts)
        
        # Recent predictions table
        st.subheader("Recent Predictions")
        if data:
            df = pd.DataFrame(data)
            df = df[["tomato_id", "class_name", "confidence", "timestamp"]].sort_values("timestamp", ascending=False).head(100)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No predictions yet")
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
else:
    st.error("Database not configured")
```

### 3.5 Deploy to HF Spaces

1. Create `.streamlit/secrets.toml` in Space settings (Settings → Repo secrets):

```toml
SUPABASE_URL = "https://xxxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

2. Push files to HF Space:

```bash
git clone https://huggingface.co/spaces/your-username/tomato-detection
cd tomato-detection
cp app.py .
cp Dockerfile .
cp requirements.txt .
git add .
git commit -m "Initial commit"
git push
```

---

## Part 4: Supabase Setup (Cloud Database)

### 4.1 Create Supabase Project

1. Go to https://supabase.com
2. Sign up → New Project
3. Fill form:
   - Name: `tomato-detection`
   - Password: Strong password
   - Region: `ap-southeast-1` (for Indonesia)
   - Plan: **Free**
4. Wait 1-2 minutes

### 4.2 Get API Keys

Settings → API → Copy:
- `SUPABASE_URL`
- `anon public` key as `SUPABASE_KEY`

Add to HF Spaces secrets.

### 4.3 Create `predictions` Table

Go to Table Editor → New Table:

```sql
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tomato_id VARCHAR(50) UNIQUE NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  class INT2 NOT NULL,
  class_name VARCHAR(20) NOT NULL,
  confidence FLOAT8 NOT NULL,
  method VARCHAR(20) DEFAULT 'single',
  servo_action VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_predictions_timestamp ON predictions(timestamp DESC);
CREATE INDEX idx_predictions_class ON predictions(class);
```

---

## Complete Setup Checklist

### Raspberry Pi
- [ ] Install Ubuntu/Raspberry Pi OS
- [ ] Create `rasp/` directory with all files
- [ ] Create `.env` with MQTT broker and HF token
- [ ] Install dependencies: `pip install -r requirements_rasp.txt`
- [ ] Connect camera (Logitech C270) via USB
- [ ] Connect ESP32 via serial (USB)
- [ ] Test camera: `python camera_handler.py`
- [ ] Install & start mosquitto: `sudo systemctl start mosquitto`
- [ ] Run: `python rasp.py`

### Windows Server
- [ ] Create `server/` directory with files
- [ ] Create `.env` with HF Spaces API endpoint
- [ ] Install dependencies: `pip install -r requirements_server.txt`
- [ ] Run: `python server.py`

### Hugging Face Spaces
- [ ] Create new Docker space at huggingface.co/spaces
- [ ] Create Supabase project & get API keys
- [ ] Add `SUPABASE_URL` and `SUPABASE_KEY` to HF Spaces secrets
- [ ] Push files: `app.py`, `Dockerfile`, `requirements.txt`
- [ ] Space auto-deploys
- [ ] Verify at `https://your-username-tomato-detection.hf.space`

### Database (Supabase)
- [ ] Create free Supabase project
- [ ] Create `predictions` table with SQL script
- [ ] Copy API keys to HF Spaces secrets

---

## Testing Workflow

1. **Test API:**
```bash
curl -X POST "https://your-username-tomato-detection.hf.space/api/insert_prediction" \
  -H "Content-Type: application/json" \
  -d '{
    "tomato_id": "tm_test_001",
    "timestamp": "2025-11-30T15:45:30Z",
    "class": 0,
    "class_name": "ripe",
    "confidence": 0.95,
    "method": "single",
    "servo_action": "gate_to_box_1"
  }'
```

2. **Check HF Spaces Dashboard:**
Visit `https://your-username-tomato-detection.hf.space` → Should see data

3. **End-to-End Test:**
- Run `rasp.py` on Pi
- Run `server.py` on Windows
- Place tomato in front of camera
- IR sensor triggers → capture → inference → MQTT → API → Supabase → Dashboard ✓

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MQTT connection refused | Check broker IP, ensure mosquitto running: `sudo systemctl status mosquitto` |
| Camera not found | List devices: `python -c "from camera_handler import list_available_cameras; list_available_cameras()"` |
| API 500 error | Check HF Spaces logs, verify Supabase keys in secrets.toml |
| Dashboard shows no data | Wait for MQTT → API → Supabase sync (~5-10 seconds) |
| Supabase "Auth token invalid" | Use `anon public` key, not `service_role` |

---

## Next Steps

1. ✅ Deploy each component separately
2. ✅ Test communication path: Pi → MQTT → Server → API → Supabase
3. ✅ Monitor dashboard for live predictions
4. ✅ Train custom YOLO model and update on Pi
5. ✅ Scale to production

---

## Notes for Contributors

- **All credentials in `.env` files** - never commit secrets
- **MQTT defaults to localhost** - change broker IP for remote setup
- **HF Spaces free tier:** 24GB disk, 16GB RAM, auto-sleeps after inactivity
- **Supabase free tier:** 500MB PostgreSQL, unlimited API calls
- **Estimated cost:** $0/month (all free tiers!)

Good luck! 🍅
