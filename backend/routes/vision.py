from flask import Blueprint, jsonify

vision_bp = Blueprint('vision', __name__, url_prefix='/vision')

@vision_bp.route('/status')
def get_vision_status():
    # Placeholder for vision status
    return jsonify({'status': 'ok'})