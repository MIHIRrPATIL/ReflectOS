from core.patches import apply_patches
apply_patches()

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Import Blueprints
from routes.object_route import object_bp
from routes.outfit_route import outfit_bp 
from routes.ocr_route import ocr_bp
from routes.task_routes import task_bp
from routes.spotify_routes import spotify_bp
from routes.expense_routes import expense_bp

# Import Services
from services.ai_service import ai_service
from services.volume_service import set_volume, reset_volume_buffer

app = Flask(__name__)
socketio = SocketIO()

def create_app():
    CORS(app)
    app.register_blueprint(object_bp, url_prefix='/api/object')
    app.register_blueprint(outfit_bp, url_prefix='/api/outfit')
    app.register_blueprint(ocr_bp, url_prefix='/api/ocr')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(spotify_bp, url_prefix='/api/spotify')
    app.register_blueprint(expense_bp, url_prefix='/api/expenses')

    @app.route('/')
    def health_check():
        return {"status": "ReflectOS Backend Online", "version": "1.1"}

    socketio.init_app(
        app, 
        cors_allowed_origins="*",
        max_http_buffer_size=10 * 1024 * 1024, # 10MB to handle large TTS payloads
        ping_timeout=60, # 60s for long AI execution turns
        ping_interval=25,
        async_mode='eventlet'
    )
    
    # Inject Emitter into AI Service
    def socket_emitter(msg_id, msg_type, payload):
        socketio.emit('message', {"uuid": msg_id, "type": msg_type, "payload": payload})
    
    ai_service.set_emitter(socket_emitter)
    
    return app

@socketio.on('message')
def handle_multiplexed_message(msg):
    """
    Unified entry point for all WebSocket messages.
    Delegates to appropriate services.
    """
    msg_id = msg.get("uuid")
    msg_type = msg.get("type")
    payload = msg.get("payload", {})
    image_data = payload.get("image")

    print(f"[SOCKET] Message Received: type={msg_type}, uuid={msg_id}")

    if msg_type == "INTERRUPT":
        ai_service.handle_interrupt()
        emit('message', {"uuid": msg_id, "type": "RESPONSE", "payload": {"status": "interrupted"}})

    elif msg_type == "VOICE_COMMAND":
        command_text = payload.get("command", "")
        print(f"[STT] Voice Command: {command_text}")
        # ALWAYS run in background to keep socket heartbeats alive
        socketio.start_background_task(
            ai_service.process_stt_logic, 
            command_text, 
            msg_id=msg_id, 
            image_data=image_data
        )

    elif msg_type == "TOOL_CALL":
        action = payload.get("action")
        print(f"[TOOL] Tool Call (Menu): {action}")
        
        intent_map = {
            "OCR": "OCR",
            "VISION": "OBJECT_DETECTION",
            "OBJECT_DETECTION": "OBJECT_DETECTION",
            "SPOTIFY": "SPOTIFY_PLAYBACK"
        }
        
        intent = intent_map.get(action)
        if intent:
            fake_command = f"Run {action}"
            # Run in background
            socketio.start_background_task(
                ai_service.process_stt_logic, 
                fake_command, 
                msg_id=msg_id, 
                image_data=image_data, 
                forced_intents=[intent]
            )
        else:
            emit('message', {"uuid": msg_id, "type": "RESPONSE", "payload": {"status": "error", "error": f"Unknown tool: {action}"}})

    elif msg_type == "GESTURE":
        gesture = payload.get("gesture", "")
        print(f"[GESTURE] Received: {gesture}")
        
        if gesture.startswith("VOLUME:"):
            try:
                level = int(gesture.split(":")[1])
                set_volume(level)
            except Exception as e:
                print(f"[ERROR] Volume parsing: {e}")
        else:
            reset_volume_buffer()
        
        emit('message', {"uuid": msg_id, "type": "RESPONSE", "payload": {"status": "gesture_processed"}})

    else:
        print(f"[SOCKET] Unknown message type: {msg_type}")
        emit('message', {"uuid": msg_id, "type": "RESPONSE", "payload": {"status": "error", "error": "Unknown type"}})

@socketio.on('connect')
def handle_connect():
    print("[SOCKET] Client Connected (Multiplexed)")

if __name__ == "__main__":
    app = create_app()
    ai_service.preload_models()
    print("[SYSTEM] Starting ReflectOS Backend (Modular) on port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
