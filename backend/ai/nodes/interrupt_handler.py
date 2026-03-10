from ai.core.state import ReflectState

INTERRUPTED_KEYWORDS = [
    "stop",
    "cancel",
    "pause",
    "exit",
    "quit",
]

def interrupt_handler_node(state: ReflectState):
    state["current_node"] = "interrupt_handler"
    state["execution_path"] = state.get("execution_path", []) + ["interrupt_handler"]
    
    from services.ai_service import ai_service
    # 1. Check if another command has taken over (Global Sync)
    if ai_service.active_command_id != state.get("request_id"):
        print(f"[INTERRUPT] Node detected outdated request_id ({state.get('request_id')}). Killing execution.")
        state["interrupted"] = True
        state["response"] = "Execution terminated."
        return state

    # 2. Check for keywords in locally
    text = state["user_input"].lower()
    if any(keyword in text for keyword in INTERRUPTED_KEYWORDS):
        print(f"[INTERRUPT] Keyword detected in input: {text}")
        state["interrupted"] = True
        state["response"] = "Execution terminated."
        # Invalidate globally so other concurrent nodes (if any) stop too
        ai_service.handle_interrupt()
    else:
        state["interrupted"] = False
    return state