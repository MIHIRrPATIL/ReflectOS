from ai.core.state import ReflectState
from core.db import db_manager
import sqlite3
import json
from datetime import datetime

def preference_node(state: ReflectState):
    """
    Template node for updating user preferences (UPDATE_PREFERENCE).
    Extracts preference data and updates the persistent context + SQLite Layer 4.
    """
    entities = state.get("extracted_entities", {})
    user_id = state.get("user_id", "default")
    
    print(f"[PREFERENCES] Updating for user: {user_id}")
    
    # 1. Identify what changed
    # e.g. "always remember my name is Mihir" -> {"user_name": "Mihir"}
    new_prefs = entities.get("preferences", {})
    
    if not new_prefs:
        # Fallback: check if 'target' was used as a value and 'key' was intended
        target = entities.get("target")
        if target and "remember" in state.get("user_input", "").lower():
             # Heuristic check for "remember X"
             pass

    # 2. Update SQLite (Layer 4 Persistent Memory)
    if new_prefs:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            for key, value in new_prefs.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO user_memories (user_id, key, value, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, key, str(value), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            print(f"[PREFERENCES] SQLite Layer 4 update successful for {len(new_prefs)} keys.")
        except Exception as e:
            print(f"[ERROR] Preference SQLite update: {e}")

    # 3. Update Current State Context
    current_prefs = state["context"].get("user_preferences", {})
    current_prefs.update(new_prefs)
    state["context"]["user_preferences"] = current_prefs
    
    tool_output = {
        "status": "success",
        "updated_keys": list(new_prefs.keys()),
        "message": f"I've updated your preferences and I'll remember this: {json.dumps(new_prefs)}"
    }
    
    # Update State
    state["tool_outputs"]["preferences"] = tool_output
    state["current_node"] = "preference_node"
    state["execution_path"] = state.get("execution_path", []) + ["preference_node"]
    
    return state
