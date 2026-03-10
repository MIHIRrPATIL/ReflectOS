import os
from ai.core.state import ReflectState, IntentType
from utils.ai_helpers import parse_ai_content
from ai.core.local_llm import LocalLLM
import json
import requests

# OpenRouter Config
from ai.core.config import OPENROUTER_API_KEY_3, OPENROUTER_MODEL, OPENROUTER_URL

def response_generator_node(state: ReflectState):
    """
    Generates response using OpenRouter (Gemini) based on intent and context.
    """
    from services.ai_service import ai_service
    if state.get("interrupted") or ai_service.active_command_id != state.get("request_id"):
        print(f"[RESPONSE] Node skipped due to interrupt (Request: {state.get('request_id')})")
        state["interrupted"] = True
        return state

    print("[RESPONSE] Generating final cohesive response")
    
    # Metadata
    state["current_node"] = "response_generator"
    state["execution_path"] = state.get("execution_path", []) + ["response_generator"]

    intent = state.get("intent")
    user_input = state.get("user_input")
    context = state.get("context", {})
    tool_outputs = state.get("tool_outputs", {})
    skills_history = state.get("skills_history", {})
    user_prefs = context.get("user_preferences", {})
    
    if state.get("interrupted"):
        # Response already set by interrupt handler
        return state

    # Construct prompt
    system_message = (
        "You are ReflectOS, a helpful and highly capable AI assistant. "
        "Your goal is to provide a single, cohesive, and natural response based on the data provided by various specialized tools (skills).\n\n"
    )

    if user_prefs:
        system_message += f"--- PERMANENT USER FACTS & PREFERENCES ---\n{json.dumps(user_prefs, indent=2)}\n\n"

    system_message += (
        f"User Input: {user_input}\n"
        f"Current Intent: {intent}\n"
    )

    if tool_outputs:
        system_message += f"\n--- CURRENT TOOL OUTPUTS ---\n{json.dumps(tool_outputs, indent=2)}\n"
    
    if skills_history:
        system_message += f"\n--- PERSISTENT SKILLS HISTORY (MEMORY) ---\n{json.dumps(skills_history, indent=2)}\n"
    
    system_message += (
        "\nINSTRUCTIONS:\n"
        "1. Synthesize all the provided tool outputs into a natural, friendly, and HUMAN-LIKE conversational response. DO NOT return JSON or raw data.\n"
        "2. CRITICAL: The CURRENT TOOL OUTPUTS section above is the GROUND TRUTH for what just happened. "
        "If it shows status 'success' and a message like 'Created event', the action WAS successful — confirm this to the user confidently. "
        "Do NOT contradict the tool output based on older conversation history where similar actions may have failed.\n"
        "3. Address each tool result briefly but cohesively.\n"
        "4. Use the PERMANENT USER FACTS (like their name) if relevant to make the response personal.\n"
        "5. If a tool's status is 'error', explain it politely. But if status is 'success', celebrate it.\n"
        "6. Be concise but helpful. Never echo the internal state or JSON structures back to the user."
    )
    
    # Create a clean message sequence for StepFun/OpenRouter
    # Standard: system, then alternating user/assistant
    messages = [{"role": "system", "content": system_message}]
    
    messages_list = state.get("messages", [])
    if len(messages_list) > 1:
        # Include last 4-6 messages for context
        # Skip the last one as we append it manually below to stay fresh
        for msg in messages_list[-6:-1]:
             raw_role = msg.type if hasattr(msg, 'type') else msg.get('role', 'user')
             content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
             
             role = "user" if raw_role in ["user", "human"] else "assistant"
             # Avoid double system or invalid roles
             if role in ["user", "assistant"]:
                 messages.append({"role": role, "content": content})

    # Always ensure the last message is the current user input
    messages.append({"role": "user", "content": user_input})

    # Content generation logic
    def generate_content(msgs):
        if OPENROUTER_API_KEY_3:
            try:
                headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY_3}", "Content-Type": "application/json"}
                payload = {"model": OPENROUTER_MODEL, "messages": msgs, "temperature": 0.7}
                resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                elif resp.status_code == 401:
                    print(f"[ERROR] OpenRouter Unauthorized (Check API Key). Status: {resp.status_code}")
                else:
                    print(f"[ERROR] OpenRouter API failed with status {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"[ERROR] OpenRouter Connection error: {e}")
        
        print(f"[RESPONSE] Using Local Fallback (Phi-3) due to OpenRouter failure or missing key.")
        return LocalLLM.get_instance().generate(msgs)

    raw_content = generate_content(messages)
    content = parse_ai_content(raw_content)
            
    state["response"] = content
    
    # Update messages sequence for native persistence (Layer 2)
    new_message = {"role": "assistant", "content": content}
    if "messages" not in state:
        state["messages"] = [new_message]
    else:
        # LangGraph State usually handles this via the annotated add_messages 
        # But here we are manually updating the state dict before returning
        state["messages"] = state.get("messages", []) + [new_message]

    print(f"[RESPONSE] Generated: {content[:50]}...")
    return state
