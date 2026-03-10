import os
import sys
import sqlite3
from unittest.mock import MagicMock

# Mock ML modules that have broken dependencies
sys.modules["ml.object_detects"] = MagicMock()
sys.modules["ml.ocr_model"] = MagicMock()
sys.modules["paddleocr"] = MagicMock()

# Ensure backend root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ai_service import AIService
from core.db import db_manager

def test_memory_persistence():
    print("--- [TEST] LONG-TERM & CONTEXT MEMORY ---")
    
    # 0. Cleanup old test data
    user_id = "test_user_memory"
    thread_id = f"{user_id}_default_session"
    
    try:
        with sqlite3.connect(db_manager.db_path, timeout=30.0) as conn:
            conn.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = ?", (thread_id,))
            conn.commit()
        print("Cleaned up old test data.")
    except Exception as e:
        print(f"Cleanup warning: {e}")

    ai = AIService.get_instance()
    
    # Turn 1: Introduce Name (Intent: UPDATE_PREFERENCE / REMEMBER)
    print("\n[TURN 1] User: Always remember my name is Mihir")
    ai.process_stt_logic("Always remember my name is Mihir", user_id=user_id)
    
    # Turn 2: Contextual Pronoun (Intent: CONVERSE / RECALL)
    # We expect Turn 1 to have saved 'Mihir' to Layer 4
    print("\n[TURN 2] User: How are you today?")
    ai.process_stt_logic("How are you today?", user_id=user_id)
    
    # Turn 3: Recall Fact (Intent: CONVERSE)
    print("\n[TURN 3] User: What is my name?")
    ai.process_stt_logic("What is my name?", user_id=user_id)
    
    # Turn 4: Contextual Continuation 
    print("\n[TURN 4] User: Tell me about Paris")
    ai.process_stt_logic("Tell me about Paris", user_id=user_id)
    
    print("\n[TURN 5] User: What's the weather there?")
    ai.process_stt_logic("What's the weather there?", user_id=user_id)

if __name__ == "__main__":
    test_memory_persistence()
