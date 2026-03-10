from flask import Blueprint, request, jsonify
from PIL import Image
import numpy as np
import io
import json
from ml.ocr_model import OCRHandler

ocr_bp = Blueprint('ocr_bp', __name__)

@ocr_bp.route('/full', methods=['POST'])
def ocr_full():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    try:
        # Load as PIL -> CV2 (numpy)
        img = Image.open(io.BytesIO(file.read())).convert("RGB")
        img_np = np.array(img)
        # PIL RGB -> OpenCV BGR (PaddleOCR works fine with RGB usually but standard cv2 is BGR)
        # Actually PaddleOCR handles standard numpy arrays. RGB is fine if we are consistent.
        # But let's convert to BGR just to be safe if using cv2 internals
        img_np = img_np[:, :, ::-1].copy() 

        ocr = OCRHandler.get_instance()
        text = ocr.process_image(img_np)
        
        return jsonify({
            "status": "success",
            "text": text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ocr_bp.route('/item', methods=['POST'])
def ocr_item():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    # Expect bbox as JSON string [x1, y1, x2, y2]
    bbox_str = request.form.get('bbox') 
    bbox = None
    if bbox_str:
        try:
            bbox = json.loads(bbox_str)
        except:
            return jsonify({"error": "Invalid bbox format. Expected JSON array [x1, y1, x2, y2]"}), 400

    try:
        img = Image.open(io.BytesIO(file.read())).convert("RGB")
        img_np = np.array(img)
        img_np = img_np[:, :, ::-1].copy() # RGB to BGR

        ocr = OCRHandler.get_instance()
        text = ocr.process_item(img_np, bbox=bbox)
        
        return jsonify({
            "status": "success",
            "text": text,
            "bbox_used": bbox
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
