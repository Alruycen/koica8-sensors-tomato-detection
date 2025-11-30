import cv2
import json
import time
import os
from datetime import datetime
import numpy as np

from ArduinoReader.arduino_reader import ArduinoReader
from CameraHandler.camera_handler import CameraHandler
from ModelLoader.load_model import load_tomato_model
from ModelLoader.preprocess import preprocess_tomato_image
from MQTTPublisher import MQTTPublisher
from config import MQTT_CONFIG, ARDUINO_CONFIG, TOMATO_CLASSES, SERVO_ACTIONS, MODEL_CONFIG, DEVICE_ID

def get_servo_action(class_idx):
    """Map class to servo action"""
    return SERVO_ACTIONS.get(class_idx, {"servo": 1, "angle": 180})

def main():
    print("🍅 Tomato Detection System Starting...")
    
    # Initialize components
    print("Initializing Arduino reader...")
    arduino = ArduinoReader(**ARDUINO_CONFIG)
    
    print("Initializing camera...")
    camera = CameraHandler(device=0)
    
    # Load model
    print("Loading YOLO model...")
    print(f"Loading custom model from HF: {MODEL_CONFIG['model_name']}")
    model = load_tomato_model(model_name=MODEL_CONFIG["model_name"])
    
    if model is None:
        print("Failed to load model. Exiting.")
        return
    
    print("Connecting to MQTT broker...")
    mqtt_pub = MQTTPublisher(**MQTT_CONFIG)
    if not mqtt_pub.connect():
        return
    
    time.sleep(1)  # Give time to connect
    
    # Main loop
    tomato_counter = 0    
    try:
        while True:
            # Step 1: Wait for IR signal from Arduino
            ir_data = arduino.read_ir_signal()
            if not ir_data:
                time.sleep(0.1)
                continue
            
            print(f"\nTomato #{tomato_counter + 1} detected by IR sensor")
            
            # Step 2: Capture image
            image = camera.capture()
            #image = camera.capture_multiple()
            if image is None:
                print("Failed to capture frame")
                continue
            
            # Step 3: Preprocess
            preprocessed = preprocess_tomato_image(image)
            
            # Step 4: Inference
            y_pred = model.predict(preprocessed)
            class_idx = int(np.argmax(y_pred))
            confidence = float(np.max(y_pred))
            class_name = TOMATO_CLASSES.get(class_idx, "-1")
            
            # Step 5: Create prediction payload
            timestamp = datetime.utcnow().isoformat() + "Z"
            tomato_id = f"tm_{int(time.time())}_{tomato_counter:03d}"
            
            servo_action = get_servo_action(class_idx)
            
            prediction_payload = {
                "tomato_id": tomato_id,
                "device_id": DEVICE_ID,
                "class": class_idx,
                "class_name": class_name,
                "confidence": confidence,
                "rasp_timestamp": timestamp,
            }
            
            # Step 6: Publish to MQTT
            mqtt_pub.publish_message(prediction_payload)
            
            # Step 7: Control servo
            print(f"🎯 Class: {class_name} | Confidence: {confidence:.2%} | Servo: Box {class_idx + 1}")
            arduino.send_servo_command(servo_action["servo"], servo_action["angle"])
            
            # Step 9: Save and delete temp image (for several days in Trash)
            # temp_image_path = f"/tmp/{tomato_id}.jpg"
            # cv2.imwrite(temp_image_path, image)
            # print(f"📸 Temp image saved: {temp_image_path}")
            
            # time.sleep(0.1)
            # try:
            #     os.remove(temp_image_path)
            #     print(f"🗑️  Temp image deleted: {temp_image_path}")
            # except Exception as e:
            #     print(f"⚠️  Failed to delete image: {e}")
            
            tomato_counter += 1
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹ Shutting down...")
    finally:
        mqtt_pub.disconnect()
        camera.release()

if __name__ == "__main__":
    main()
