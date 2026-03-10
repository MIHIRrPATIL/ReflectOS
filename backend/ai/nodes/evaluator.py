import json
import requests
from ai.core.state import ReflectState
from ai.core.local_llm import LocalLLM
from utils.ai_helpers import extract_json, parse_ai_content
from ai.core.config import OPENROUTER_MODEL, OPENROUTER_URL, OPENROUTER_API_KEY

def evaluator_node(state: ReflectState):
    """
    Evaluates current tool outputs against user intent.
    Decides if the results are 'SATISFACTORY' or need 'REFINEMENT'.
    """
    state["current_node"] = "evaluator"
    state["execution_path"] = state.get("execution_path", []) + ["evaluator"]
    
    print(f"[EVALUATOR] Iteration {state.get('iterations', 0)} - Starting evaluation")
    
    user_input = state.get("user_input")
    tool_outputs = state.get("tool_outputs", {})
    iterations = state.get("iterations", 0)
    MAX_ITERATIONS = 2 # Total 3 attempts (0, 1, 2)

    if iterations >= MAX_ITERATIONS:
        print("[EVALUATOR] Max iterations reached. Proceeding to response generator.")
        state["status"] = "SATISFACTORY"
        return state

    # Prompt Engineering for Evaluation
    system_prompt = (
        "You are the Quality Evaluator for ReflectOS. "
        "Your goal is to determine if the AI's current progress satisfies the user's request.\n\n"
        "USER REQUEST: " + user_input + "\n\n"
        "CURRENT TOOL OUTPUTS:\n" + json.dumps(tool_outputs, indent=2) + "\n\n"
        "INSTRUCTIONS:\n"
        "1. Analyze if the tool results provide a complete and high-quality answer.\n"
        "2. If the results are poor, incomplete, or don't match the user's intent (e.g., wrong song genre, empty weather data), suggest a REFINEMENT.\n"
        "3. If results are good, mark as SATISFACTORY.\n"
        "4. Return ONLY a JSON object: {\"status\": \"SATISFACTORY\" | \"REFINEMENT\", \"critique\": \"Reason or suggestion for improvement\"}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Evaluate the current progress and return the JSON status."}
    ]

    try:
        if OPENROUTER_API_KEY:
            print(f"[EVALUATOR] Sending request to OpenRouter ({OPENROUTER_MODEL})...")
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                url=OPENROUTER_URL,
                headers=headers,
                data=json.dumps({"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0.0}),
                timeout=30
            )
            response.raise_for_status()
            raw_content = response.json()["choices"][0]["message"]["content"]
            print("[EVALUATOR] OpenRouter response received.")
        else:
            print("[EVALUATOR] Using Local LLM for evaluation...")
            local_llm = LocalLLM.get_instance()
            raw_content = local_llm.generate(messages)
            print("[EVALUATOR] Local LLM response received.")

        evaluation = extract_json(parse_ai_content(raw_content))
        status = evaluation.get("status", "SATISFACTORY")
        critique = evaluation.get("critique", "")

        state["status"] = status # Set explicit status for graph
        if status == "REFINEMENT":
            print(f"[EVALUATOR] Result: REFINEMENT requested. Critique: {critique}")
            if "critiques" not in state or state["critiques"] is None:
                state["critiques"] = []
            state["critiques"].append(critique)
            state["iterations"] = state.get("iterations", 0) + 1
        else:
            print("[EVALUATOR] Result: SATISFACTORY.")
            state["status"] = "SATISFACTORY"

    except Exception as e:
        print(f"[ERROR] Evaluator step failed: {e}. Defaulting to satisfactory.")
        # We don't want to loop forever on errors
        state["status"] = "SATISFACTORY"

    return state
