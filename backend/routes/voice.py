from flask import Blueprint, jsonify

voice_bp = Blueprint('voice', __name__, url_prefix='/voice')

@voice_bp.route('/listen')
def listen():
    # Placeholder for voice listen endpoint
    return jsonify({'message': 'listening'})