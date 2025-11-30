from ultralytics import YOLO
from huggingface_hub import hf_hub_download
import os

def load_tomato_model(model_name="yolov8n", cache_dir="/tmp/hf_models"):
    """
    Load YOLO model - custom fine-tuned from Hugging Face
    
    Args:
        model_name (str): 
            - Custom HF: "your-username/tomato-yolo" (when use_huggingface=True)
        cache_dir (str): Directory to cache HF models locally
    
    Returns:
        YOLO model object, or None if failed
    
    Examples:
        # Load pre-trained nano (default)
        model = load_tomato_model()
        
        # Load pre-trained small
        model = load_tomato_model("yolov8s")
        
        # Load custom fine-tuned from HF
        model = load_tomato_model("your-username/tomato-yolo", use_huggingface=True)
    """
    print(f"Loading custom model from HF: {model_name}...")
    
    try:
        # Download model from HF
        model_path = hf_hub_download(
            repo_id=model_name,
            filename="best.pt",  # Standard fine-tuned model filename
            cache_dir=cache_dir,
        )
        
        print(f"✓ Downloaded from HF: {model_path}")
        
        # Load into YOLO
        model = YOLO(model_path)
        
        model_size = os.path.getsize(model_path) / (1024 * 1024)
        print(f"Loaded custom model ({model_size:.1f} MB)")
        
        return model
    
    except Exception as e:
        print(f"Failed to download from HF: {e}")
        return None