from ai.core.state import ReflectState
from ai.core.config import OPENROUTER_API_KEY_3, OPENROUTER_MODEL, OPENROUTER_URL
from ai.core.local_llm import LocalLLM
from utils.ai_helpers import extract_json
import requests
import json

def validator_node(state: ReflectState):
    """
    AI Guard Node: Validates the intended tool call before execution.
    Checks for correctness, safety, and alignment with user intent.
    """
    user_input = state.get("user_input", "")
    intent = state.get("intent")
    history = state.get("history", [])
    
    print(f"[VALIDATOR] Checking intent: {intent}")

    if not intent:
        return state

    # If it's a critical tool (DB or System), we perform a deep check
    critical_intents = [
        "MANAGE_EXPENSES", "ADD_TASK", "UPDATE_PREFERENCE", 
        "MANAGE_CALENDAR", "SYSTEM_MEDIA_CONTROL"
    ]
    
    intent_str = intent.value if hasattr(intent, 'value') else str(intent)
    
    if intent_str not in critical_intents:
        print(f"[VALIDATOR] {intent_str} is not a critical intent. Skipping deep check.")
        state["validation_status"] = "PASSED"
        return state

    system_prompt = (
        "You are an AI Security & Correctness Guard for ReflectOS. "
        "Your job is to intercept a user request and an identified intent, and decide if the system is about to make a correct and safe tool call. "
        "You must output JSON with 'status' (VALID/INVALID) and 'critique' (reasoning).\n\n"
        "Rules:\n"
        "1. If the user wants to delete something, ensure it's explicit.\n"
        "2. If it's a financial transaction, verify the account and amount logic.\n"
        "3. If the intent seems wrong for the input, mark as INVALID.\n\n"
        "Output Format: {\"status\": \"VALID\" | \"INVALID\", \"critique\": \"explanation\"}"
    )

    user_prompt = (
        f"User Input: {user_input}\n"
        f"Identified Intent: {intent_str}\n"
        "Should we proceed with this tool call?"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    result = None
    if OPENROUTER_API_KEY_3:
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY_3}", "Content-Type": "application/json"}
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0}
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"]
                result = extract_json(raw)
        except Exception as e:
            print(f"[VALIDATOR] Error: {e}")

    if not result:
        # Fallback to local or default to VALID (don't block if AI is down, but log it)
        print("[VALIDATOR] API Failed. Defaulting to PASSED.")
        state["validation_status"] = "PASSED"
        return state

    status = result.get("status", "VALID")
    critique = result.get("critique", "")

    if status == "INVALID":
        print(f"[VALIDATOR] ❌ REJECTED: {critique}")
        state["validation_status"] = "REJECTED"
        state["critique"] = critique
        # We set refined_intent to try and help the classifier
        state["status"] = "REFINEMENT" 
    else:
        print(f"[VALIDATOR] ✅ APPROVED: {critique}")
        state["validation_status"] = "PASSED"

    state["execution_path"] = state.get("execution_path", []) + ["validator_node"]
    return state
