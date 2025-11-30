import serial
import json

class ArduinoReader:
    def __init__(self, 
                 port='/dev/ttyUSB0', # port
                 baud=115200, # baud rate
                 ):
        self.ser = serial.Serial(port, baud, timeout=1)
    
    def read_ir_signal(self):
        """Blocks until tomato detected"""
        if self.ser.in_waiting:
            line = self.ser.readline().decode('utf-8').strip()
            try:
                data = json.loads(line)
                return data  # {"ir_detected": true, "timestamp": "..."}
            except Exception as e:
                print(e)
                return None
    
    def send_servo_command(self, servo_id, angle):
        """Tell ESP32 to move servo"""
        cmd = json.dumps({"servo": servo_id, "angle": angle})
        self.ser.write(cmd.encode() + b'\n')