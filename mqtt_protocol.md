# MQTT Communication Protocol for Tomato Detection System

## Overview
MQTT is used to send tomato detection predictions from Raspberry Pi to Windows Server.

**Broker:** localhost:1883 (mosquitto on your network)
**Protocol:** MQTT v3.1.1
**QoS:** 1 (at least once delivery)

---

## MQTT Topics & Payload Structure

### 1. Main Topic: `tomato/predictions`

**Published by:** Raspberry Pi (rasp.py)
**Subscribed by:** Windows Server (server.py)
**Frequency:** When tomato detected by IR sensor + processed by YOLO

**Payload (JSON):**
```json
{
  "tomato_id": "tm_20251130_154530_001",
  "timestamp": "2025-11-30T15:45:30.123456Z",
  "class": 0,
  "class_name": "ripe",
  "confidence": 0.9542,
  "method": "single",
  "servo_action": "gate_to_box_1"
}
```

**Field Descriptions:**

| Field | Type | Example | Purpose |
|-------|------|---------|---------|
| `tomato_id` | string | `tm_20251130_154530_001` | Unique ID per tomato (timestamp + counter) |
| `timestamp` | ISO 8601 | `2025-11-30T15:45:30.123456Z` | When prediction made (UTC) |
| `class` | int | `0` | YOLO class index (0=ripe, 1=unripe, 2=damaged, 3=old) |
| `class_name` | string | `"ripe"` | Human-readable class |
| `confidence` | float | `0.9542` | Model confidence 0.0-1.0 |
| `method` | string | `"single"` | Prediction method (`"single"`, `"tta"`, etc) |
| `servo_action` | string | `"gate_to_box_1"` | Which servo action to execute |

**NOTE:** `image_path` removed. Images saved locally on Pi are automatically deleted after MQTT publish to prevent storage bloat.

---

### 2. Optional Topic: `tomato/arduino/ir_signal`

**Published by:** Raspberry Pi (arduino_reader.py)
**Subscribed by:** (for monitoring only)
**Frequency:** When IR sensor detects tomato

**Payload (JSON):**
```json
{
  "ir_detected": true,
  "timestamp": "2025-11-30T15:45:29.500000Z",
  "sensor_id": 25
}
```

---

### 3. Optional Topic: `tomato/servo/status`

**Published by:** Raspberry Pi (after sending servo command)
**Subscribed by:** Windows Server (for logging)
**Frequency:** After each servo action

**Payload (JSON):**
```json
{
  "servo_id": 1,
  "angle": 90,
  "timestamp": "2025-11-30T15:45:31.000000Z",
  "status": "success"
}
```

---

## Python Implementation

### Raspberry Pi Side (rasp/mqtt_publisher.py)

```python
import paho.mqtt.client as mqtt
import json
from datetime import datetime
from config import MQTT_CONFIG

class MQTTPublisher:
    def __init__(self, broker_host, broker_port=1883):
        """Initialize MQTT client"""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.connected = False
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker"""
        if rc == 0:
            print(f"✓ Connected to MQTT broker {self.broker_host}:{self.broker_port}")
            self.connected = True
        else:
            print(f"✗ Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected"""
        if rc != 0:
            print(f"⚠ Unexpected disconnection. Code: {rc}")
        self.connected = False
    
    def on_publish(self, client, userdata, mid):
        """Callback when message published"""
        print(f"✓ Message published (mid={mid})")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()  # Start background thread
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def publish_prediction(self, prediction_data):
        """
        Publish tomato prediction to MQTT
        
        Args:
            prediction_data (dict): {
                "tomato_id": str,
                "timestamp": str (ISO 8601),
                "class": int,
                "class_name": str,
                "confidence": float,
                "method": str,
                "servo_action": str
            }
        """
        if not self.connected:
            print("✗ Not connected to MQTT broker")
            return False
        
        try:
            topic = "tomato/predictions"
            payload = json.dumps(prediction_data)
            
            # Publish with QoS=1 (at least once)
            result = self.client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✓ Published to {topic}: {prediction_data['tomato_id']}")
                return True
            else:
                print(f"✗ Publish failed: {result.rc}")
                return False
        
        except Exception as e:
            print(f"✗ Error publishing: {e}")
            return False
    
    def publish_ir_signal(self, timestamp):
        """Publish IR sensor detection"""
        if not self.connected:
            return False
        
        try:
            topic = "tomato/arduino/ir_signal"
            payload = json.dumps({
                "ir_detected": True,
                "timestamp": timestamp,
                "sensor_id": 25
            })
            self.client.publish(topic, payload, qos=1)
            return True
        except Exception as e:
            print(f"✗ Error publishing IR signal: {e}")
            return False
    
    def publish_servo_status(self, servo_id, angle, status="success"):
        """Publish servo action status"""
        if not self.connected:
            return False
        
        try:
            topic = "tomato/servo/status"
            payload = json.dumps({
                "servo_id": servo_id,
                "angle": angle,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": status
            })
            self.client.publish(topic, payload, qos=1)
            return True
        except Exception as e:
            print(f"✗ Error publishing servo status: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from broker"""
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker")
```

### Raspberry Pi Side (rasp/config.py)

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# MQTT Configuration
MQTT_CONFIG = {
    "broker_host": os.getenv("MQTT_BROKER", "localhost"),  # or "192.168.1.100"
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
    "device": 0,  # /dev/video0
    "width": 1280,
    "height": 720,
    "fps": 30
}

# Model Settings
MODEL_CONFIG = {
    "model_name": "your-username/tomato-yolo",  # HF Hub
    "target_size": 640,
    "inference_method": "single",  # "single", "tta", or "adaptive"
}
```

### Raspberry Pi Side (rasp/.env)

```
# .env (create this file, don't commit to git)
MQTT_BROKER=localhost
MQTT_PORT=1883
HF_TOKEN=hf_xxxxxxxxxxxx  # Your HF token for private models
```

### Raspberry Pi Main (rasp/rasp.py - Simplified with MQTT)

```python
# rasp.py
import cv2
import json
import time
import os
from datetime import datetime
import numpy as np

from arduino_reader import ArduinoReader
from camera_handler import CameraHandler
from model_loader import load_tomato_model
from preprocess import preprocess_fast
from inference import TomatoInference
from mqtt_publisher import MQTTPublisher
from config import MQTT_CONFIG, TOMATO_CLASSES, SERVO_ACTIONS, MODEL_CONFIG

def get_servo_action(class_idx):
    """Map class to servo action"""
    return SERVO_ACTIONS.get(class_idx, {"servo": 1, "angle": 180})

def main():
    print("🍅 Tomato Detection System Starting...")
    
    # Initialize components
    print("Initializing Arduino reader...")
    arduino = ArduinoReader(port='/dev/ttyUSB0', baud=115200)
    
    print("Initializing camera...")
    camera = CameraHandler(device=0)
    
    print("Loading YOLO model from Hugging Face...")
    model = load_tomato_model(MODEL_CONFIG["model_name"])
    
    print("Initializing inference engine...")
    inference = TomatoInference(model, use_tta=False)
    
    print("Connecting to MQTT broker...")
    mqtt_pub = MQTTPublisher(**MQTT_CONFIG)
    if not mqtt_pub.connect():
        print("✗ Failed to connect to MQTT broker. Exiting.")
        return
    
    time.sleep(1)  # Give time to connect
    
    # Main loop
    tomato_counter = 0
    print("\n✓ System ready! Waiting for tomatoes...")
    
    try:
        while True:
            # Step 1: Wait for IR signal from Arduino
            ir_data = arduino.read_ir_signal()
            if not ir_data:
                time.sleep(0.1)
                continue
            
            print(f"\n📍 Tomato #{tomato_counter + 1} detected by IR sensor")
            mqtt_pub.publish_ir_signal(ir_data.get("timestamp"))
            
            # Step 2: Capture image
            frame = camera.capture()
            if frame is None:
                print("✗ Failed to capture frame")
                continue
            
            # Step 3: Preprocess
            preprocessed = preprocess_fast(frame, target_size=640)
            
            # Step 4: Inference
            y_prob = inference.predict_single(preprocessed)
            class_idx = int(np.argmax(y_prob))
            confidence = float(np.max(y_prob))
            class_name = TOMATO_CLASSES.get(class_idx, "unknown")
            
            # Step 5: Create prediction payload (NO image_path)
            timestamp = datetime.utcnow().isoformat() + "Z"
            tomato_id = f"tm_{int(time.time())}_{tomato_counter:03d}"
            
            servo_action = get_servo_action(class_idx)
            
            prediction_payload = {
                "tomato_id": tomato_id,
                "timestamp": timestamp,
                "class": class_idx,
                "class_name": class_name,
                "confidence": confidence,
                "method": "single",
                "servo_action": f"gate_to_box_{class_idx + 1}"
            }
            
            # Step 6: Publish to MQTT
            mqtt_pub.publish_prediction(prediction_payload)
            
            # Step 7: Control servo
            print(f"🎯 Class: {class_name} | Confidence: {confidence:.2%} | Servo: Box {class_idx + 1}")
            arduino.send_servo_command(servo_action["servo"], servo_action["angle"])
            
            # Step 8: Publish servo status
            time.sleep(0.5)  # Wait for servo to move
            mqtt_pub.publish_servo_status(
                servo_id=servo_action["servo"],
                angle=servo_action["angle"],
                status="success"
            )
            
            # Step 9: Save image locally for temporary logging (optional)
            temp_image_path = f"/tmp/tomato_{tomato_id}.jpg"
            cv2.imwrite(temp_image_path, frame)
            print(f"📸 Temp image saved: {temp_image_path}")
            
            # Step 10: Delete image immediately to prevent disk bloat
            time.sleep(0.1)  # Brief delay to ensure write completes
            try:
                os.remove(temp_image_path)
                print(f"🗑️  Temp image deleted: {temp_image_path}")
            except Exception as e:
                print(f"⚠️  Failed to delete image: {e}")
            
            tomato_counter += 1
            time.sleep(1)  # Wait before next detection
    
    except KeyboardInterrupt:
        print("\n\n⏹ Shutting down...")
    finally:
        mqtt_pub.disconnect()
        camera.release()
        print("✓ Shutdown complete")

if __name__ == "__main__":
    main()
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────┐
│         RASPBERRY PI (rasp.py)          │
├─────────────────────────────────────────┤
│ 1. IR Sensor → Arduino detected tomato  │
│ 2. Capture frame (Logitech C270)        │
│ 3. Preprocess (resize 1280×720→640×640) │
│ 4. YOLO inference (get class + conf)    │
│ 5. Create prediction JSON (no image)    │
│ 6. Publish MQTT                         │
│ 7. Save temp image → Delete immediately │
└─────────────────┬───────────────────────┘
                  │
          MQTT Publish
          topic: "tomato/predictions"
                  │
                  ↓
┌─────────────────────────────────────────┐
│    MQTT Broker (localhost:1883)         │
└─────────────────┬───────────────────────┘
                  │
          MQTT Subscribe
                  │
                  ↓
┌─────────────────────────────────────────┐
│      WINDOWS SERVER (server.py)         │
├─────────────────────────────────────────┤
│ 1. Receive MQTT message                 │
│ 2. Parse JSON payload                   │
│ 3. Insert into Supabase PostgreSQL      │
│ 4. Update Streamlit dashboard (live)    │
└─────────────────────────────────────────┘
```

---

## Testing MQTT Locally

### Install Mosquitto (MQTT Broker)

**On Ubuntu/WSL:**
```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

**On Windows:**
- Download from mosquitto.org
- Or use Docker: `docker run -p 1883:1883 eclipse-mosquitto`

### Test Publishing & Subscribing

**Terminal 1 (Subscribe to predictions):**
```bash
mosquitto_sub -h localhost -p 1883 -t "tomato/predictions" -v
```

**Terminal 2 (Publish test message):**
```bash
mosquitto_pub -h localhost -p 1883 -t "tomato/predictions" -m '{
  "tomato_id": "tm_test_001",
  "timestamp": "2025-11-30T15:45:30Z",
  "class": 0,
  "class_name": "ripe",
  "confidence": 0.95,
  "method": "single",
  "servo_action": "gate_to_box_1"
}'
```

**Expected output in Terminal 1:**
```
tomato/predictions {
  "tomato_id": "tm_test_001",
  ...
}
```

---

## Summary: Key Changes

| Aspect | Before | After | Reason |
|--------|--------|-------|--------|
| `image_path` in payload | Included | **Removed** | Not sent over MQTT, saves bandwidth |
| Image handling | Saved only | **Saved → Auto-deleted** | Prevents disk bloat on Pi |
| Storage on Pi | Persistent | **Temporary** | Keeps /tmp clean |
| Supabase integration | N/A from Pi | **N/A (handled by server)** | Centralized architecture |

---

## Summary

| Topic | Publisher | Subscriber | Frequency | Purpose |
|-------|-----------|-----------|-----------|---------|
| `tomato/predictions` | Pi (rasp.py) | Server (server.py) | Per tomato (~0.5-2.5s) | Main detection data (no image) |
| `tomato/arduino/ir_signal` | Pi (arduino_reader) | Optional | Per tomato | Debug: IR detection timing |
| `tomato/servo/status` | Pi (rasp.py) | Optional | Per tomato | Debug: Servo movement |

All payloads use **JSON format** for easy parsing on server side. Images processed in-memory and deleted after MQTT publish for efficiency.
