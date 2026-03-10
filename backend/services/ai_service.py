import uuid
import base64
import cv2
import numpy as np
import re
from ai.graph.graph import build_graph
from ai.core.local_llm import LocalLLM
from ml.object_detects import ObjectDetector
from ml.ocr_model import OCRHandler
from utils.tts import generate_tts_base64

class AIService:
    _instance = None
    
    def __init__(self):
        self.ai_app = build_graph()
        self.ai_context = {"history": []}
        self.active_command_id = None
        self.socket_emitter = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance

    def set_emitter(self, emitter_fn):
        """Allows app.py to inject the socket emit function."""
        self.socket_emitter = emitter_fn

    def preload_models(self):
        print("[SYSTEM] Preloading AI Models...")
        try:
            LocalLLM.get_instance().load_model()
            ObjectDetector.get_instance()
            OCRHandler.get_instance()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to preload models: {e}")
            return False

    def handle_interrupt(self):
        print("[AI_SERVICE] INTERRUPT RECEIVED. Invalidating active command.")
        self.active_command_id = None

    def _decode_base64_image(self, base64_str):
        """Converts base64 image data to numpy array (OpenCV format)."""
        if not base64_str:
            return None
        try:
            # Handle data:image/jpeg;base64,... prefix
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            
            img_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"[ERROR] Image decoding failed: {e}")
            return None

    def process_stt_logic(self, command_text, msg_id=None, image_data=None, forced_intents=None, user_id="local_user", session_id="default_session"):
        # If no msg_id (internal call), generate one
        current_request_id = msg_id if msg_id else str(uuid.uuid4())
        self.active_command_id = current_request_id
        
        if not command_text:
            return

        from ai.core.state import create_initial_state, ExecutionStatus

        # Initialize State with Thread Identity
        initial_state = create_initial_state(
            user_id=user_id,
            session_id=session_id,
            user_input=command_text,
            input_mode="vision" if image_data else "voice",
            image_data=image_data,
            request_id=current_request_id
        )

        # Only decode image for vision-related actions (menu-triggered)
        vision_intents = {"OCR", "OBJECT_DETECTION", "OUTFIT", "DESCRIBE_SCENE"}
        is_vision_action = forced_intents and any(i in vision_intents for i in forced_intents)
        if image_data and is_vision_action:
            print(f"[AI] Decoding image data (size: {len(image_data)} chars)...")
            initial_state["image"] = self._decode_base64_image(image_data)
            if initial_state["image"] is not None and self.socket_emitter:
                self.socket_emitter(current_request_id, "VISION_CAPTURE", {"status": "success"})

        # Apply overrides (like forced intents from menu)
        if forced_intents:
            initial_state["intent"] = forced_intents[0]
            initial_state["intent_confidence"] = 1.0

        thread_id = initial_state["thread_id"]
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

        # Run AI Graph
        try:
            print(f"[AI] Invoking graph for thread: {thread_id}")
            result = self.ai_app.invoke(initial_state, config=config)

            if self.active_command_id != current_request_id:
                 print(f"[INTERRUPT] Command {current_request_id} interrupted during AI thinking.")
                 return
            
            # Response Extraction from New State
            # final response is stored in result["messages"] via LangGraph or manually in result["response"]
            # To stay legacy compatible for now, let's see where response generator puts it
            response_text_raw = result.get("response", "")
            
            # If empty, try to get last message content
            if not response_text_raw and result.get("messages"):
                last_msg = result["messages"][-1]
                if last_msg.get("role") == "assistant":
                    response_text_raw = last_msg.get("content", "")

            if isinstance(response_text_raw, list):
                response_text_raw = " ".join([str(x) for x in response_text_raw])
            
            response_text = re.sub(r'[\*\#\_`]', '', str(response_text_raw)).strip()
            
            audio_base64 = None
            if self.active_command_id != current_request_id:
                 print(f"[INTERRUPT] Command {current_request_id} interrupted before TTS.")
                 return

            if response_text:
                print(f"[TTS] Submitting to generator (text len: {len(response_text)} chars)...")
                audio_base64 = generate_tts_base64(response_text)
                if audio_base64:
                    print(f"[TTS] Generator returned audio (base64 size: {len(audio_base64)} chars).")
                else:
                    print("[TTS] Generator returned nothing.")
            
            intent = result.get("intent")
            print(f"[AI] Response: {response_text} (Intent: {intent})")
            
            # Detection of conversation continuation
            should_listen = False
            if intent == "CONVERSE" or (response_text and response_text.strip().endswith("?")):
                 should_listen = True

            if self.active_command_id != current_request_id:
                 print(f"[INTERRUPT] Command {current_request_id} interrupted before emission.")
                 return

            # Response Payload
            payload = {
                "status": "processed", 
                "command": command_text,
                "response": response_text,
                "audio": audio_base64,
                "intent": str(intent) if intent else None,
                "should_listen": should_listen,
                "tool_outputs": result.get("tool_outputs", {})
            }

            if self.socket_emitter:
                print(f"[AI] Final emission for UUID {current_request_id}...")
                self.socket_emitter(current_request_id, "RESPONSE", payload)
                print(f"[AI] Emission complete for UUID {current_request_id}.")
            else:
                print(f"[ERROR] No socket_emitter registered for {current_request_id}.")
            
            # Update Layer 3-5 Hooks (Future)
            # self.post_execution_updates(result, user_id, session_id)
            
        except Exception as e:
            print(f"[ERROR] AI Service processing error: {e}")
            import traceback
            traceback.print_exc()
            if self.socket_emitter:
                self.socket_emitter(current_request_id, "RESPONSE", {"status": "error", "error": str(e)})

ai_service = AIService.get_instance()
