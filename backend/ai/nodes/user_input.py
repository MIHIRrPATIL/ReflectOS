from ai.core.state import ReflectState

def user_input_node(state: ReflectState):
    state["current_node"] = "user_input"
    state["execution_path"] = state.get("execution_path", []) + ["user_input"]
    # Ensure context is initialized if not present
    if "context" not in state or state["context"] is None:
        state["context"] = {}
    
    # Just passing through, input is already in state when graph starts
    return state