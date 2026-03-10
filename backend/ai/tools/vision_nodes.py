import cv2
import numpy as np
import tempfile
import os
import json
import requests
from ai.core.state import ReflectState
from ml.object_detects import ObjectDetector
from ml.ocr_model import OCRHandler
from ml.outfit_model import analyze_outfit
from ai.core.local_llm import LocalLLM
from ai.core.config import OPENROUTER_API_KEY_4, OPENROUTER_MODEL
from utils.ai_helpers import parse_ai_content

# --- LLM HELPERS ---
def llm_vision_vlm(image_base64, prompt):
    """
    Sends base64 image data to a VLM (Vision-Language Model) via OpenRouter.
    """
    if not image_base64:
        return "Error: No image data provided for VLM analysis."
    
    # Use user-requested model
    VLM_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"
    
    # Ensure data URI prefix
    if not image_base64.startswith("data:"):
        image_base64 = f"data:image/jpeg;base64,{image_base64}"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    }
                }
            ]
        }
    ]
    
    if OPENROUTER_API_KEY_4:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY_4}",
                "Content-Type": "application/json"
            }
            data = {
                "model": VLM_MODEL,
                "messages": messages,
                "temperature": 0.2
            }
            response = requests.post(url, headers=headers, json=data, timeout=45)
            if response.status_code == 200:
                result = response.json()
                print(f"[VLM] Response received from {VLM_MODEL}")
                return parse_ai_content(result['choices'][0]['message']['content']).strip()
            else:
                print(f"[ERROR] VLM Request failed ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"[ERROR] VLM analysis failed: {e}")

    return "Vision analysis currently unavailable. (VLM Failure)"

def llm_cleanup_ocr(text):
    """Uses LLM to clean and summarize raw OCR text (Legacy Fallback)."""
    if not text.strip():
        return "No text found to clean."
    
    system_prompt = "You are an OCR cleanup assistant. Clean, fix typos, and reconstruct the following raw OCR text into a coherent, readable format. Preserve ALL meaningful text, lists, and numbers. Do not over-summarize; the user needs to know what the document actually says."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Raw OCR Text:\n{text}"}
    ]
    
    # Try OpenRouter first
    if OPENROUTER_API_KEY_4:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY_4}",
                "Content-Type": "application/json"
            }
            data = {
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.3
            }
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                print("[OCR] OpenRouter cleanup response received (Fallback Mode).")
                return parse_ai_content(result['choices'][0]['message']['content']).strip()
        except Exception as e:
            print(f"[ERROR] OpenRouter OCR cleanup failed: {e}")

    # Fallback to Local LLM
    try:
        print("[OCR] Running Local LLM cleanup (Fallback Mode)...")
        llm = LocalLLM.get_instance()
        return llm.generate(messages).strip()
    except Exception as e:
        print(f"[ERROR] Local OCR cleanup failed: {e}")
        return text # Return raw if LLM fails

# --- VISION NODES ---

def vllm_node(state: ReflectState):
    """Primary VLM Node. Handles OCR, Outfit, and Scene analysis using Nemotron-Nano."""
    print("[VLLM] Node Triggered")
    from ai.core.state import IntentType
    
    state["current_node"] = "vllm_node"
    state["execution_path"] = state.get("execution_path", []) + ["vllm_node"]
    state["vllm_failed"] = False

    image_base64 = state.get("image_data")
    if not image_base64:
        print("[VLLM] No image data. Failing to fallback.")
        state["vllm_failed"] = True
        return state

    intent = state.get("intent")
    user_input = state.get("user_input", "")
    target = state["context"].get("target_object")

    # Construct prompt based on intent
    if intent == IntentType.READ_TEXT:
        prompt = "Read and transcribe ALL text visible in this image accurately. Maintain structure. If no text, say 'No text detected.'"
        if target:
            prompt = f"Find the text on the {target} and read it. " + prompt
        output_key = "ocr"
    elif intent == IntentType.OUTFIT_ANALYSIS:
        prompt = f"Analyze the user's outfit. Identify clothes (type, color) and provide style feedback. User asked: '{user_input}'"
        output_key = "outfit_analysis"
    elif intent == IntentType.DESCRIBE_SCENE:
        prompt = f"Describe what you see in this image in detail. Focus on: {target if target else 'everything'}."
        output_key = "object_detection"
    else:
        # Unexpected intent for this node
        state["vllm_failed"] = True
        return state

    try:
        print(f"[VLLM] Calling VLM for {intent}...")
        result = llm_vision_vlm(image_base64, prompt)
        
        if "Failure" in result or "unavailable" in result:
             print("[VLLM] VLM Service returned failure. Triggering fallback.")
             state["vllm_failed"] = True
             return state

        if "tool_outputs" not in state or state["tool_outputs"] is None:
            state["tool_outputs"] = {}

        # Standardize outputs for the evaluator
        if intent == IntentType.READ_TEXT:
            state["tool_outputs"][output_key] = {"raw_text": result, "cleaned_text": result, "used_vlm": True}
        elif intent == IntentType.OUTFIT_ANALYSIS:
            state["tool_outputs"][output_key] = {"suggestions": result, "used_vlm": True}
        else:
            state["tool_outputs"][output_key] = {"description": result, "used_vlm": True}

        print(f"[VLLM] {intent} analysis successful.")
            
    except Exception as e:
        print(f"[ERROR] VLLM Node error: {e}")
        state["vllm_failed"] = True
        
    return state

def object_detection_node(state: ReflectState):
    """Detects objects as a tool (Legacy Fallback). Pops intent and populates tool_outputs."""
    from services.ai_service import ai_service
    if state.get("interrupted") or ai_service.active_command_id != state.get("request_id"):
        print(f"[VISION] Detection node skipped due to interrupt (Request: {state.get('request_id')})")
        state["interrupted"] = True
        return state

    print("[VISION] Object Detection Node Triggered (Legacy Fallback)")
    
    # Maintenance
    state["current_node"] = "object_detection_node"
    state["execution_path"] = state.get("execution_path", []) + ["object_detection_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    frame = state.get("image")
    if frame is None:
        state["tool_outputs"]["object_detection"] = {"error": "Camera frame not available in state."}
        return state

    target = state["context"].get("target_object")
    
    try:
        detector = ObjectDetector.get_instance()
        detections = detector.detect(frame)
        
        # Persistent memory update
        if "skills_history" not in state or state["skills_history"] is None:
            state["skills_history"] = {}
        state["skills_history"]["last_objects"] = detections
        
        # Filter if target specified
        filtered = detections
        if target:
            filtered = [d for d in detections if target.lower() in d['label'].lower()]
            print(f"[VISION] Filtering for target '{target}': Found {len(filtered)} matches.")

        state["tool_outputs"]["object_detection"] = {
            "count": len(filtered),
            "objects": filtered,
            "full_scan_count": len(detections),
            "target": target,
            "used_vlm": False
        }
        
        # Persistent memory sync
        state["skills_history"]["object_detection"] = state["tool_outputs"]["object_detection"]
            
    except Exception as e:
        print(f"[ERROR] Object detection error: {e}")
        state["tool_outputs"]["object_detection"] = {"error": str(e)}
        
    return state

def ocr_node(state: ReflectState):
    """Performs smart OCR as a tool (Legacy Fallback). Pops intent and populates tool_outputs."""
    print("[OCR] Node Triggered (Legacy Fallback)")
    
    # Maintenance
    state["current_node"] = "ocr_node"
    state["execution_path"] = state.get("execution_path", []) + ["ocr_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    frame = state.get("image")
    if frame is None:
        state["tool_outputs"]["ocr"] = {"error": "Camera frame not available in state."}
        return state

    target = state["context"].get("target_object")
    
    try:
        print("[OCR] Processing image with PaddleOCR (Full Frame)...")
        ocr = OCRHandler.get_instance()
        raw_text = ocr.process_image(frame)
        print(f"[OCR] Raw text extracted ({len(raw_text)} chars).")
        
        cleaned_text = ""
        if raw_text.strip():
            print("[OCR] Starting LLM cleanup...")
            cleaned_text = llm_cleanup_ocr(raw_text)
            print("[OCR] LLM cleanup finished.")
        
        state["tool_outputs"]["ocr"] = {
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "used_vlm": False,
            "target": target
        }
        
        if "skills_history" not in state or state["skills_history"] is None:
            state["skills_history"] = {}
        state["skills_history"]["last_ocr"] = state["tool_outputs"]["ocr"]
            
    except Exception as e:
        print(f"[ERROR] OCR error: {e}")
        state["tool_outputs"]["ocr"] = {"error": str(e)}
        
    return state

def outfit_analysis_node(state: ReflectState):
    """Analyzes outfit as a tool (Legacy Fallback). Pops intent and populates tool_outputs."""
    print("[OUTFIT] Analysis Node Triggered (Legacy Fallback)")
    
    # Maintenance
    state["current_node"] = "outfit_analysis_node"
    state["execution_path"] = state.get("execution_path", []) + ["outfit_analysis_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    frame = state.get("image")
    if frame is None:
        state["tool_outputs"]["outfit_analysis"] = {"error": "Camera frame not available in state."}
        return state

    user_input = state.get("user_input", "").lower()
    
    try:
        detector = ObjectDetector.get_instance()
        detections = detector.detect(frame)
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp:
            cv2.imwrite(temp.name, frame)
            temp_path = temp.name
            
        try:
            results = analyze_outfit(temp_path)
            
            state["tool_outputs"]["outfit_analysis"] = {
                "suggestions": str(results),
                "objects_seen": detections,
                "used_vlm": False
            }
            
            if "skills_history" not in state or state["skills_history"] is None:
                state["skills_history"] = {}
            state["skills_history"]["last_outfit"] = state["tool_outputs"]["outfit_analysis"]
                
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"[ERROR] Outfit analysis error: {e}")
        state["tool_outputs"]["outfit_analysis"] = {"error": str(e)}
        
    return state
