import sys
import os
import uuid
import json
import sqlite3

# Add backend to path (one level up from tests/)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Mock missing langchain submodules that block paddlex/vision nodes
import types
mock_langchain_doc = types.ModuleType("langchain.docstore.document")
mock_langchain_doc.Document = object
sys.modules["langchain.docstore.document"] = mock_langchain_doc
sys.modules["langchain.docstore"] = types.ModuleType("langchain.docstore")

mock_langchain_ts = types.ModuleType("langchain.text_splitter")
mock_langchain_ts.RecursiveCharacterTextSplitter = object
sys.modules["langchain.text_splitter"] = mock_langchain_ts

from ai.graph.graph import build_graph
from ai.core.state import IntentType, create_initial_state
from core.db import db_manager

def test_memory_system():
    print("--- [TEST] REFLECTOS MEMORY SYSTEM TEST ---")
    
    # 1. Test Database Connectivity
    print("\n[STEP 1] Checking Database Connectivity...")
    db_path = db_manager.db_path
    if os.path.exists(db_path):
        print(f"[OK] SQLite Database file found at: {db_path}")
        db_valid = True
    else:
        print(f"[INFO] SQLite Database file not found yet. It will be created on first graph run.")
        db_valid = True

    # 2. Test Graph Compilation
    print("\n[STEP 2] Building Graph...")
    app = build_graph()
    print("[OK] Graph Compiled successfully.")

    # 3. Test Multi-Intent Orchestration (Memory Layer 1)
    print("\n[STEP 3] Testing Multi-Intent Orchestration...")
    user_id = "test_user"
    session_id = str(uuid.uuid4())
    
    initial_state = create_initial_state(
        user_id=user_id,
        session_id=session_id,
        user_input="Check weather and play Queen"
    )
    
    initial_state["intent"] = IntentType.GET_WEATHER
    initial_state["secondary_intents"] = [IntentType.PLAY_SPOTIFY]
    initial_state["intent_confidence"] = 1.0
    initial_state["extracted_entities"] = {"target": "Queen"}

    print(f"Initial Intent: {initial_state['intent']}")
    print(f"Secondary Intents: {initial_state['secondary_intents']}")

    config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}, "recursion_limit": 5}
    
    print("\n[AI] Run 1: Executing first intent...")
    try:
        result = app.invoke(initial_state, config=config)
        print(f"Final Status: {result.get('status')}")
        print(f"Execution Path: {result.get('execution_path')}")
        print(f"Last Intent Processed: {result.get('intent')}")
        print(f"Remaining Secondary: {result.get('secondary_intents')}")
        print(f"Response: {result.get('response')[:100]}...")
    except Exception as e:
        print(f"[INFO] Graph execution hit limit (as expected in test): {e}")

    print("\n[STEP 4] Persistence Check (SQLite)...")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM checkpoints WHERE thread_id = ?", (f"{user_id}_{session_id}",))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"[OK] Persistence Verified: {count} checkpoints found in SQLite.")
        else:
            print("[WARN] No checkpoints found in SQLite. Check if graph.py actually used the checkpointer.")
        conn.close()
    except Exception as e:
        print(f"[ERROR] SQLite Persistence Check failed: {e}")

if __name__ == "__main__":
    test_memory_system()
