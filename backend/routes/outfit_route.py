from flask import Blueprint, request, jsonify
from PIL import Image
import io
import os
import tempfile
# Import logic from existing outfit_model
from ml.outfit_model import analyze_outfit 

outfit_bp = Blueprint('outfit_bp', __name__)

@outfit_bp.route('/detect', methods=['POST'])
def detect_outfit():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # outfit_model.analyze_outfit currently expects a FILE POSIX PATH, not a PIL image.
        # We need to save the uploaded file temporarily.
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as temp:
            file.save(temp.name)
            temp_path = temp.name
            
        try:
            # Run analysis
            results = analyze_outfit(temp_path)
            
            # Clean up temp file
            os.remove(temp_path)
            
            if not results:
                 return jsonify({"status": "no_detection", "data": []})

            return jsonify({
                "status": "success",
                "data": results
            })
            
        except Exception as inner_e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise inner_e

    except Exception as e:
        print(f"Error in /outfit/detect: {e}")
        return jsonify({"error": str(e)}), 500
