// TO BE CONTINUED

#include <ArduinoJson.h>

const int IR_PIN = 25;         // IR sensor input, contoh 25
const int SERVO_PINS[] = {12, 14, 27};  // 3 servos, contoh 12, 14, 27

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