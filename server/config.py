# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# MQTT Configuration
MQTT_CONFIG = {
    "broker_host": os.getenv("MQTT_BROKER", ""),
    "broker_port": int(os.getenv("MQTT_PORT", 1883)),
    "api_endpoint": os.getenv("API_ENDPOINT", ""),
}