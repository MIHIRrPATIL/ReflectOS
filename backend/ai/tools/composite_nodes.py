import requests
from ai.core.state import ReflectState, IntentType
from ai.core.config import OPENROUTER_API_KEY_4, OPENROUTER_MODEL, OPENROUTER_URL
from ai.core.local_llm import LocalLLM
from utils.ai_helpers import extract_json

def composite_node(state: ReflectState):
    """
    Decomposes a complex request into a sequence of smaller tasks.
    Each task has an intent and its specific entities.
    """
    user_input = state.get("user_input", "")
    print(f"[COMPOSITE] Decomposing: {user_input}")

    system_prompt = (
        "You are the Task Decomposer for ReflectOS. "
        "Break the user's complex goal into a sequence of small, atomic tasks.\n\n"
        "Available Intents:\n"
        "- CONVERSE: General chat, jokes, or knowledge.\n"
        "- SEARCH_WEB: Look up real-time info.\n"
        "- GET_WEATHER: Check current weather.\n"
        "- PLAY_SPOTIFY: Play a song/track.\n"
        "- PLAY_YOUTUBE: Search/Play a video.\n"
        "- READ_TEXT: OCR/Read from camera.\n"
        "- DESCRIBE_SCENE: Object detection/VLLM description.\n"
        "- READ_TASKS: Show/Read todo list.\n"
        "- SYSTEM_MEDIA_CONTROL: Volume/Media commands.\n\n"
        "Output ONLY a JSON array of tasks: [{\"intent\": \"INTENT_NAME\", \"entities\": {\"track\": \"name\", \"query\": \"search string\", \"target\": \"item\"}}].\n"
        "Example: 'Tell me a joke and play some jazz' -> "
        "[{\"intent\": \"CONVERSE\", \"entities\": {\"target\": \"joke\"}}, "
        "{\"intent\": \"PLAY_SPOTIFY\", \"entities\": {\"track\": \"jazz\"}}]"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    raw_content = None
    if OPENROUTER_API_KEY_4:
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY_4}", "Content-Type": "application/json"}
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0}
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ERROR] Composite OpenRouter failed: {e}")

    if not raw_content:
        print("[COMPOSITE] Using Local Fallback for decomposition...")
        raw_content = LocalLLM.get_instance().generate(messages)

    try:
        task_list = extract_json(raw_content)
        if not isinstance(task_list, list):
            # Try to find a list in the dict if LLM returned a wrapped object
            if isinstance(task_list, dict) and "tasks" in task_list:
                task_list = task_list["tasks"]
            else:
                task_list = []

        if task_list:
            print(f"[COMPOSITE] Decomposed into {len(task_list)} steps.")
            # Set up the queue in context
            first_task = task_list[0]
            remaining = task_list[1:]
            
            # Update state with the first task immediately
            state["intent"] = IntentType(first_task["intent"]) if first_task.get("intent") in IntentType.__members__ else IntentType.CONVERSE
            state["extracted_entities"] = first_task.get("entities", {})
            
            # Save the rest to the queue
            state["context"]["task_queue"] = remaining
            state["tool_outputs"]["composite"] = {
                "status": "success",
                "plan": [t.get("intent") for t in task_list]
            }
        else:
            state["tool_outputs"]["composite"] = {"status": "failed", "error": "No tasks decomposed"}
            
    except Exception as e:
        print(f"[ERROR] Composite decomposition parsing: {e}")
        state["tool_outputs"]["composite"] = {"status": "error", "error": str(e)}

    # Maintenance
    state["current_node"] = "composite_node"
    state["execution_path"] = state.get("execution_path", []) + ["composite_node"]
    
    return state
