from MQTTSubscriber.mqtt_client import MQTTSubscriber
from config import MQTT_CONFIG

def main():   
    # Validate required configuration
    if not MQTT_CONFIG["api_endpoint"]:
        print("Error: API_ENDPOINT not set in .env")
        return
    
    # Initialize subscriber
    subscriber = MQTTSubscriber(**MQTT_CONFIG)
    
    # Connect to broker
    if not subscriber.connect():
        print("Failed to connect to MQTT broker")
        return
    
    print("System ready! Listening for tomato predictions...\n")
    
    # Keep running
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n\n⏹ Shutting down...")
        subscriber.disconnect()
        print("✓ Disconnected")

if __name__ == "__main__":
    main()
