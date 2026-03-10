from ai.core.state import ReflectState, IntentType
from core.db import db_manager
import sqlite3

def context_manager_node(state: ReflectState):
    """
    Manages context updates and Intent Orchestration for multi-step tasks.
    """
    print("[CONTEXT] Updating conversation history and intents")
    
    # 1. Update Conversation History (Legacy Field)
    context = state.get("context", {})
    history = context.get("history", [])
    
    # In the new schema, we might use result["messages"] instead of manual history
    # but for Phase 1 we keep it for backward compatibility.
    if state.get("user_input"):
        # Avoid duplicates if history already has this input
        if not history or history[-1].get("content") != state["user_input"]:
            history.append({"role": "user", "content": state["user_input"]})
    
    if len(history) > 10:
        history = history[-10:]
    
    context["history"] = history
    state["context"] = context

    # 1b. Load Layer 4 Permanent Memories (if not already merged)
    if "memories_loaded" not in context:
        user_id = state.get("user_id", "default")
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_memories WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                print(f"[CONTEXT] Loading {len(rows)} permanent memories from Layer 4.")
                current_prefs = context.get("user_preferences", {})
                for key, value in rows:
                    if key not in current_prefs: # Don't overwrite session-specific overrides
                        current_prefs[key] = value
                context["user_preferences"] = current_prefs
            
            context["memories_loaded"] = True
            state["context"] = context
        except Exception as e:
            print(f"[ERROR] Loading Layer 4 memories: {e}")

    # 2. Intent Orchestration (Sequential Execution)
    path = state.get("execution_path", [])
    print(f"[CONTEXT] Current Path Length: {len(path)}. Last 3: {path[-3:]}")
    
    # Identify if we just finished a "tool" or "skill" node.
    # Standard: tools end in '_node' and aren't core nodes.
    # Also check current_node vs the last item in path to avoid double-processing
    just_finished_tool = False
    if path:
        last_node = path[-1]
        if last_node.endswith("_node") and last_node not in ["intent_classifier", "context_manager", "user_input"]:
            just_finished_tool = True

    if just_finished_tool:
        active_intent = state.get('intent')
        print(f"[CONTEXT] Tool execution detected ({path[-1]}). Consuming intent: {active_intent}")
        
        # 1. Check Task Queue (Composite Tasks with specific entities)
        task_queue = context.get("task_queue", [])
        if task_queue:
            next_task = task_queue.pop(0)
            context["task_queue"] = task_queue # Save updated queue
            
            raw_intent = next_task.get("intent")
            state["intent"] = IntentType(raw_intent) if raw_intent in IntentType.__members__ else IntentType.CONVERSE
            state["extracted_entities"] = next_task.get("entities", {})
            
            # Sync context mappings for nodes that use state["context"]
            context["track_name"] = state["extracted_entities"].get("track")
            context["target_object"] = state["extracted_entities"].get("target") or context["track_name"]
            
            print(f"[CONTEXT] Promoted next task from queue: {state['intent']} with entities: {state['extracted_entities']}")
            state["context"] = context
            return state

        # 2. Check Legacy Secondary Intents (Enums only)
        secondary = state.get("secondary_intents", [])
        if secondary:
            state["intent"] = secondary[0]
            state["secondary_intents"] = secondary[1:]
            print(f"[CONTEXT] Promoted next intent: {state['intent']}")
        else:
            state["intent"] = None # All done, proceed to evaluator
            print("[CONTEXT] All intents processed. Routing to evaluator.")

    # Maintenance: Add self to path
    state["current_node"] = "context_manager"
    state["execution_path"] = path + ["context_manager"]

    print(f"[CONTEXT] Current Intent after orchestration: {state.get('intent')}")
    return state
