import cv2
import numpy as np
from config import CAMERA_CONFIG

class CameraHandler:
    """
    Handle camera operations for tomato detection
    Supports USB cameras (Logitech C270) and built-in cameras
    """
    
    def __init__(self, device=0, width=1280, height=720, fps=30):
        """
        Initialize camera handler
        
        Args:
            device (int): Camera device index (0 = /dev/video0)
            width (int): Frame width in pixels (default: 1280)
            height (int): Frame height in pixels (default: 720)
            fps (int): Frames per second (default: 30)
        """
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.is_open = False
        
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Initialize and configure camera"""
        try:
            print(f"Initializing camera device {self.device}...")
            self.cap = cv2.VideoCapture(self.device)
            
            if not self.cap.isOpened():
                print(f"Failed to open camera device {self.device}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Auto-focus disabled for consistent depth/focus
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            
            # Read a dummy frame to initialize
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to read from camera")
                return False
            
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            print(f"Camera initialized: {actual_width}×{actual_height} @ {actual_fps} FPS")
            self.is_open = True
            return True
        
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False
    
    def capture(self, retry_count=3):
        """
        Capture a single frame from camera
        
        Args:
            retry_count (int): Number of retries if capture fails
        
        Returns:
            numpy array (BGR frame) or None if failed
        """
        if not self.is_open:
            print("Camera not initialized")
            return None
        
        for attempt in range(retry_count):
            try:
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    return frame
                else:
                    print(f"Capture attempt {attempt + 1}/{retry_count} failed")
                    
                    if attempt < retry_count - 1:
                        import time
                        time.sleep(0.1)  # Brief delay before retry
            
            except Exception as e:
                print(f"Error capturing frame: {e}")
        
        print(f"Failed to capture frame after {retry_count} attempts")
        return None
    
    def capture_multiple(self, num_frames=3, delay_ms=50):
        """
        Capture multiple frames and return the sharpest one
        
        Useful for reducing motion blur
        
        Args:
            num_frames (int): Number of frames to capture
            delay_ms (int): Delay between captures in milliseconds
        
        Returns:
            numpy array (sharpest BGR frame) or None if failed
        """
        frames = []
        sharpness_scores = []
        
        import time
        
        for i in range(num_frames):
            frame = self.capture()
            if frame is not None:
                frames.append(frame)
                
                # Calculate Laplacian sharpness score
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                sharpness = laplacian.var()
                sharpness_scores.append(sharpness)
                
                if i < num_frames - 1:
                    time.sleep(delay_ms / 1000.0)
            else:
                print(f"Failed to capture frame {i + 1}")
        
        if not frames:
            return None
        
        # Return sharpest frame
        best_idx = np.argmax(sharpness_scores)
        print(f"Selected frame {best_idx + 1}/{num_frames} (sharpness: {sharpness_scores[best_idx]:.2f})")
        return frames[best_idx]
    
    def get_frame_info(self):
        """
        Get current camera frame properties
        
        Returns:
            dict with camera properties
        """
        if not self.is_open:
            return None
        
        try:
            info = {
                "device": self.device,
                "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": int(self.cap.get(cv2.CAP_PROP_FPS)),
                "brightness": self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
                "contrast": self.cap.get(cv2.CAP_PROP_CONTRAST),
                "saturation": self.cap.get(cv2.CAP_PROP_SATURATION),
            }
            return info
        except Exception as e:
            print(f"Error getting frame info: {e}")
            return None
    
    def set_brightness(self, value):
        """
        Set camera brightness
        
        Args:
            value (float): Brightness value (usually 0-255 or -1 to 1)
        """
        if not self.is_open:
            return False
        
        try:
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, value)
            print(f"Brightness set to {value}")
            return True
        except Exception as e:
            print(f"Error setting brightness: {e}")
            return False
    
    def set_contrast(self, value):
        """
        Set camera contrast
        
        Args:
            value (float): Contrast value
        """
        if not self.is_open:
            return False
        
        try:
            self.cap.set(cv2.CAP_PROP_CONTRAST, value)
            print(f"Contrast set to {value}")
            return True
        except Exception as e:
            print(f"Error setting contrast: {e}")
            return False
    
    def release(self):
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
            self.is_open = False
            print("✓ Camera released")
    
    def __del__(self):
        """Destructor - ensure camera is released"""
        self.release()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


# Helper function to list available cameras
def list_available_cameras():
    """
    List all available camera devices on the system
    
    Returns:
        list of available camera indices
    """
    available = []
    
    print("Scanning for available cameras...")
    
    for i in range(10):  # Check first 10 devices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"Camera {i}: /dev/video{i} ({width}×{height})")
            cap.release()
    
    if not available:
        print("No cameras found")
    
    return available