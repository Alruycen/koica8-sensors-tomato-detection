import paho.mqtt.client as mqtt
import requests
import json

class MQTTSubscriber:
    def __init__(self, broker_host, api_endpoint, broker_port=1883,):
        """
        Args:
            broker_host (str): MQTT broker address (e.g., "192.168.1.100" or "localhost")
            api_endpoint (str): HF Spaces API endpoint
        """
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.api_endpoint = api_endpoint
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker {self.broker_host}")
            self.client.subscribe("tomato/predictions")
            print("Subscribed to tomato/predictions")
        else:
            print(f"Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Unexpected disconnection. Reconnecting...")
    
    def connect(self):
        try:
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
        
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Parse MQTT payload
            payload = json.loads(msg.payload.decode())
            print(f"\nReceived: {payload['tomato_id']}")
            print(f"Class: {payload['class_name']} ({payload['confidence']:.2%})")
            
            # Forward to HF Spaces API
            self.forward_to_api(payload) # API buatan Jason
        
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {msg.payload}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
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
                print(f"Saved to database: {result.get('message', 'OK')}")
            else:
                print(f"API error ({response.status_code}): {response.text}")
        
        except requests.exceptions.Timeout:
            print(f"API timeout - retrying...")
        except requests.exceptions.ConnectionError:
            print(f"Connection error - check API endpoint")
        except Exception as e:
            print(f"Error forwarding to API: {e}")
            
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()