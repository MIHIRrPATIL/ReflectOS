from ai.core.state import ReflectState
import json

def confirmation_node(state: ReflectState):
    """
    Template node for confirming user actions (CONFIRM_ACTION).
    Handles 'Yes', 'No', 'Proceed', 'Cancel' style inputs for pending operations.
    """
    # Maintenance
    state["current_node"] = "confirmation_node"
    state["execution_path"] = state.get("execution_path", []) + ["confirmation_node"]
    
    user_input = state.get("user_input", "").lower()
    print(f"[CONFIRMATION] Processing: {user_input}")
    
    # Simple Mock logic
    is_confirmed = any(word in user_input for word in ["yes", "yeah", "sure", "proceed", "ok"])
    is_denied = any(word in user_input for word in ["no", "nope", "cancel", "stop"])
    
    status = "PENDING"
    if is_confirmed: status = "CONFIRMED"
    elif is_denied: status = "DENIED"
    
    tool_output = {
        "status": status,
        "input": user_input,
        "message": f"Action {status.lower()}."
    }
    
    # Update State
    state["tool_outputs"]["confirmation"] = tool_output
    
    return state
