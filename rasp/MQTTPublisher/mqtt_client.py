import paho.mqtt.client as mqtt
import json

class MQTTPublisher:
    def __init__(self, broker_url, broker_port=1883):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
        self.broker_url = broker_url
        self.broker_port = broker_port
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker {self.broker_host}:{self.broker_port}")
        else:
            print(f"Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Unexpected disconnection. Code: {rc}")
    
    def connect(self):
        try:
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()  # Start background thread
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def publish_message(self, prediction_data):
        """
        Publish tomato prediction to MQTT
        
        Args:
            prediction_data (dictionary object): {
                "tomato_id": str,
                "device_id": str,
                "class": int,
                "class_name": str,
                "confidence": float,
                "rasp_timestamp": str,
            }
        """
        try:
            topic = "tomato/predictions"
            payload = json.dumps(prediction_data)
            
            result = self.client.publish(topic, payload)
            
            if result[0] == 0:
                print(f"Published to {topic}: {prediction_data}")
                return True
            else:
                print(f"Publish failed: {result.rc}")
                return False
        
        except Exception as e:
            print(f"Error publishing: {e}")
            return False
    
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()