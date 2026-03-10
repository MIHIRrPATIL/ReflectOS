from flask import Blueprint, request, jsonify
from PIL import Image
import io
from ml.object_detects import ObjectDetector

object_bp = Blueprint('object_bp', __name__)

@object_bp.route('/detect', methods=['POST'])
def detect_objects():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Load image (PIL)
        img = Image.open(io.BytesIO(file.read())).convert("RGB")
        
        # Run detection
        detector = ObjectDetector.get_instance()
        detections = detector.detect(img)
        
        return jsonify({
            "status": "success",
            "count": len(detections),
            "objects": detections
        })
        
    except Exception as e:
        print(f"Error in /object/detect: {e}")
        return jsonify({"error": str(e)}), 500
