import cv2

def preprocess_tomato_image(frame, target_size=320):
    """
    Resize Logitech C270 1280x720 to YOLO input size
    """
    # YOLO input: 320x320, 416x416, 640x640, 1280x1280
    resized = cv2.resize(frame, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
    normalized = resized.astype('float32') / 255.0
    return normalized