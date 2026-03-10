import os
import torch
from ultralytics import YOLO

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Using the same OIV7 model as outfit for now, as it has 600 classes (good for general detection)
MODEL_PATH = os.path.join(BASE_DIR, "ml/models/yolov8n-oiv7.pt") 

class ObjectDetector:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        print(f"Loading Object Detector from {MODEL_PATH}...")
        if not os.path.exists(MODEL_PATH):
            print(f"WARNING: Model not found at {MODEL_PATH}. Downloading may occur or fail.")
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(MODEL_PATH)
        self.model.to(self.device)
        print("Object Detector loaded.")

    def detect(self, image_source, conf_thresh=0.25):
        """
        Detect objects in an image.
        :param image_source: PIL Image, numpy array, or file path.
        :return: List of dicts {label, conf, box: [x1, y1, x2, y2]}
        """
        results = self.model(image_source, conf=conf_thresh)
        if not results:
            return []

        detections = []
        for r in results:
            names = r.names
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()
                label = names[cls_id]
                
                detections.append({
                    "label": label,
                    "confidence": round(conf, 2),
                    "box": [round(x) for x in xyxy]
                })
        return detections
