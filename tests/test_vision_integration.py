import sys
import os
import cv2
import numpy as np
from ai.graph.graph import build_graph
from dotenv import load_dotenv

import types

# --- MONKEYPATCH FOR PADDLEOCR / LANGCHAIN COMPATIBILITY ---
try:
    import langchain.docstore.document
except ImportError:
    if "langchain.docstore" not in sys.modules:
        sys.modules["langchain.docstore"] = types.ModuleType("langchain.docstore")
    if "langchain.docstore.document" not in sys.modules:
        doc_module = types.ModuleType("langchain.docstore.document")
        try:
            from langchain_core.documents import Document
        except ImportError:
            from langchain.schema import Document
        doc_module.Document = Document
        sys.modules["langchain.docstore.document"] = doc_module
        sys.modules["langchain.docstore"].document = doc_module

try:
    import langchain.text_splitter
except ImportError:
    if "langchain.text_splitter" not in sys.modules:
        ts_module = types.ModuleType("langchain.text_splitter")
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            try:
                from langchain.text_splitter import RecursiveCharacterTextSplitter
            except ImportError:
                class RecursiveCharacterTextSplitter: pass
        ts_module.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
        sys.modules["langchain.text_splitter"] = ts_module
# --- END MONKEYPATCH ---

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

def test_vision_skills():
    print("Building Graph...")
    app = build_graph()
    
    # Mocking GestureService frame
    from cv.gesture_service import gesture_service
    # Create a blank white frame
    mock_frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
    cv2.putText(mock_frame, "HELLO WORLD", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    
    with gesture_service.ocr_lock:
        gesture_service.ocr_frame = mock_frame

    test_cases = [
        {"input": "What is this?", "expected_intent": "OBJECT_DETECTION"},
        {"input": "Read what is on the bottle.", "expected_intent": "OCR"},
        {"input": "How is the weather?", "expected_intent": "CHECK WEATHER"}
    ]

    # Persistent Context to simulate session
    session_context = {"history": []}
    skills_history = {}

    for case in test_cases:
        print(f"\nTest Case: '{case['input']}'")
        state = {
            "user_input": case['input'],
            "context": session_context,
            "interrupted": False,
            "intent": None,
            "confidence": 0.0,
            "response": None,
            "tool_data": None,
            "skills_history": skills_history
        }
        
        # We need to manually inject a detected bottle for the OCR test if YOLO is mocked
        if "bottle" in case['input']:
            print("Injecting mock 'bottle' into history for smart crop test...")
            skills_history["last_objects"] = [{"label": "bottle", "box": [50, 50, 200, 200], "confidence": 0.9}]
            state["skills_history"] = skills_history

        result = app.invoke(state)
        
        # Update session persistent data
        session_context = result.get("context", session_context)
        skills_history = result.get("skills_history", skills_history)
        
        print(f"Detected Intent: {result.get('intent')}")
        print(f"Target Object: {session_context.get('target_object')}")
        print(f"Tool Data: {list(result.get('tool_data', {}).keys()) if result.get('tool_data') else 'None'}")
        print(f"Response: {result.get('response')}")
        
        if result.get('intent') == case['expected_intent']:
            print("Status: Success")
        else:
            print(f"Status: Failure (Expected {case['expected_intent']})")

if __name__ == "__main__":
    test_vision_skills()
