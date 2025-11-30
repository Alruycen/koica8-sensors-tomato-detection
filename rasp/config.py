# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Raspberry Pi Device ID
DEVICE_ID = os.getenv("DEVICE_ID", "raspberrypi_default")

# MQTT Configuration
MQTT_CONFIG = {
    "broker_host": os.getenv("MQTT_BROKER", ""),
    "broker_port": int(os.getenv("MQTT_PORT", 1883)),
}

# Arduino Configuration
ARDUINO_CONFIG = {
    "port": os.getenv("ARDUINO_PORT", "/dev/ttyUSB0"),
    "baud": int(os.getenv("ARDUINO_BAUD", 115200)),
}

# Tomato Classes
TOMATO_CLASSES = {
    0: "unripe",
    1: "ripe",
    2: "old",
    3: "damaged"
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
    "model_name": os.getenv("MODEL_NAME", ""),  # HF Hub
    "target_size": 320,
}