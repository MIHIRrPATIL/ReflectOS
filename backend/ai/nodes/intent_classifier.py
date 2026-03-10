from ai.core.state import ReflectState, IntentType
from ai.core.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL
from ai.core.local_llm import LocalLLM
from utils.ai_helpers import parse_ai_content, extract_json

import requests
import json

def intent_classifier_node(state: ReflectState):
    """
    Classifies user intent using OpenRouter (StepFun) or Local Fallback.
    """
    from services.ai_service import ai_service
    if state.get("interrupted") or ai_service.active_command_id != state.get("request_id"):
        print(f"[INTENT] Node skipped due to interrupt (Request: {state.get('request_id')})")
        state["interrupted"] = True
        return state

    print(f"[INTENT] Classifying: {state.get('user_input')}")
    user_input = state.get("user_input", "")
    
    # Map legacy strings/LLM outputs to IntentType Enums
    INTENT_MAP = {
        "SEARCH WEB": IntentType.SEARCH_WEB,
        "CONTROL MEDIA": IntentType.SYSTEM_MEDIA_CONTROL,
        "CHECK WEATHER": IntentType.GET_WEATHER,
        "CALENDAR": IntentType.MANAGE_CALENDAR,
        "CONVERSE": IntentType.CONVERSE,
        "SYSTEM_CONTROL": IntentType.UPDATE_PREFERENCE,
        "REMEMBER_FACT": IntentType.UPDATE_PREFERENCE,
        "UPDATE_PREFERENCE": IntentType.UPDATE_PREFERENCE,
        "CONTROL_MEDIA": IntentType.SYSTEM_MEDIA_CONTROL,
        "TODO_LIST": IntentType.READ_TASKS,
        "ADD_TASK": IntentType.ADD_TASK,
        "READ_TASKS": IntentType.READ_TASKS,
        "MANAGE_TASKS": IntentType.ADD_TASK,
        "OBJECT_DETECTION": IntentType.DESCRIBE_SCENE,
        "OCR": IntentType.READ_TEXT,
        "OUTFIT_ANALYSIS": IntentType.OUTFIT_ANALYSIS,
        "SPOTIFY_PLAYBACK": IntentType.PLAY_SPOTIFY,
        "SPOTIFY_DEVICES": IntentType.SWITCH_SPOTIFY_DEVICE,
        "SPOTIFY_PLAYLISTS": IntentType.LIST_PLAYLISTS,
        "SPOTIFY_INFO": IntentType.CONTROL_SPOTIFY,
        "SWITCH_DEVICE": IntentType.SWITCH_SPOTIFY_DEVICE,
        "ADD_TO_QUEUE": IntentType.ADD_SPOTIFY_QUEUE,
        "PLAY_YOUTUBE": IntentType.PLAY_YOUTUBE,
        "COMPOSITE_TASK": IntentType.COMPOSITE_TASK,
        "EXPENSES": IntentType.MANAGE_EXPENSES,
    }

    # If already forced (e.g. from menu) with 1.0 confidence, skip
    # UNLESS we are in a refinement loop (critiques exist)
    if state.get("intent") and state.get("intent_confidence") == 1.0 and not state.get("critiques"):
        print(f"[INTENT] Skipping classification (Forced: {state['intent']})")
        return state

    messages_list = state.get("messages", [])
    if len(messages_list) > 1:
        # Get last 5 messages (excluding current user input which is handled in prompt)
        recent = messages_list[-6:-1] 
        history_lines = []
        for m in recent:
            raw_role = m.type if hasattr(m, 'type') else m.get('role', 'user')
            role = "USER" if raw_role in ["user", "human"] else "ASSISTANT"
            content = m.content if hasattr(m, 'content') else m.get('content', '')
            history_lines.append(f"{role}: {content}")
        history_context = "\nRECENT CONVERSATION:\n" + "\n".join(history_lines)
    else:
        history_context = ""

    system_message = (
        "You are the Intent Classifier for ReflectOS. "
        "Categorize the user's message into EXACTLY ONE of these categories:\n\n"
        "1. 'SEARCH WEB': Questions requiring real-time info (news, sports, specific facts).\n"
        "2. 'CHECK WEATHER': Weather queries.\n"
        "3. 'CALENDAR': Dates, meetings, schedules.\n"
        "4. 'CONVERSE': General knowledge, greetings, or chat.\n"
        "5. 'TODO_LIST': Managing tasks.\n"
        "6. 'OBJECT_DETECTION': 'What is this?'.\n"
        "7. 'OCR': 'Read this text' or 'What does this say?'.\n"
        "8. 'OUTFIT_ANALYSIS': Analyze what the user is WEARING, clothing advice, style feedback, or 'How do I look?'. Example: 'What am I wearing?'.\n"
        "9. 'SPOTIFY_PLAYBACK': Commands to PLAY music, songs, or playlists. Use this for general 'play music' requests unless YouTube is explicitly mentioned.\n"
        "10. 'SPOTIFY_PLAYLISTS': Commands to LIST or SHOW available playlists.\n"
        "11. 'CONTROL MEDIA': Volume/media controls.\n"
        "12. 'REMEMBER_FACT': Requests to remember permanent personal facts.\n"
        "13. 'SWITCH_DEVICE': Requests to switch Spotify playback to another device.\n"
        "14. 'ADD_TO_QUEUE': Requests to add a song to the Spotify queue.\n"
        "15. 'CLEAR_QUEUE': Requests to clear or empty the Spotify queue.\n"
        "16. 'PLAY_YOUTUBE': Commands to SEARCH for or PLAY a video on YouTube.\n"
        "17. 'COMPOSITE_TASK': Complex requests that require multiple independent actions. Example: 'Tell me a joke AND play some jazz' or 'Search for news then show my tasks'.\n"
        "18. 'EXPENSES': Money, spending, income, transfers between accounts, debts (who owes whom), balance inquiries, financial summaries.\n"
        f"{history_context}\n\n"
        "Rule: Return ONLY JSON: {\"intents\": [\"CATEGORY\"], \"entities\": {\"track\": \"song name\", \"target\": \"item\", \"device\": \"device\"}}."
    )
    
    # Create alternating message sequence
    messages = [{"role": "system", "content": system_message}]
    
    messages_list = state.get("messages", [])
    if len(messages_list) > 1:
        # Include history for context
        for m in messages_list[-6:-1]:
            raw_role = m.type if hasattr(m, 'type') else m.get('role', 'user')
            role = "user" if raw_role in ["user", "human"] else "assistant"
            content = m.content if hasattr(m, 'content') else m.get('content', '')
            
            # Avoid duplicate system or invalid roles
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})

    # Ensure the last message is always the current user input
    messages.append({"role": "user", "content": user_input})

    # ... Handle Critiques ...
    critiques = state.get("critiques", [])
    if critiques:
        critique_msg = "\n\nCRITICAL: PREVIOUS CLASSIFICATION FAILED. Evaluator critique:\n" + "\n".join(critiques)
        # Append to system message directly
        messages[0]["content"] += critique_msg
    
    def process_raw_result(raw):
        if not raw:
            print("[ERROR] Classifier returned empty response.")
            return [IntentType.CONVERSE], {}
        try:
            data = extract_json(raw)
            raw_intents = data.get("intents", []) or [data.get("intent")]
            mapped_intents = [INTENT_MAP[i.strip().upper()] for i in raw_intents if i and i.strip().upper() in INTENT_MAP]
            
            if not mapped_intents:
                mapped_intents = [IntentType.CONVERSE]
                
            entities = data.get("entities", {})
            # Backward compatibility for flat JSON keys
            if not entities:
                 entities = {k: v for k, v in data.items() if k not in ["intents", "intent"]}
            
            return mapped_intents, entities
        except Exception as e:
            print(f"[ERROR] Intent parsing: {e}")
            # Keyword-based fallback when JSON parsing fails
            # ONLY scan user input (not raw LLM output, which may contain misleading keywords)
            combined = user_input.lower()
            
            KEYWORD_INTENT_MAP = {
                IntentType.MANAGE_CALENDAR: ["schedule", "meeting", "calendar", "appointment"],
                IntentType.PLAY_SPOTIFY: ["play", "song", "music", "spotify", "change the song", "next song", "pause", "resume"],
                IntentType.GET_WEATHER: ["weather", "temperature", "forecast", "rain"],
                IntentType.SEARCH_WEB: ["search", "google", "look up", "find out"],
                IntentType.DESCRIBE_SCENE: ["what is this", "what do you see", "describe", "detect"],
                IntentType.READ_TEXT: ["read this", "ocr", "what does this say"],
                IntentType.OUTFIT_ANALYSIS: ["outfit", "wearing", "how do i look", "clothes"],
                IntentType.PLAY_YOUTUBE: ["youtube", "video"],
                IntentType.UPDATE_PREFERENCE: ["remember", "my name is", "i prefer", "i like"],
                IntentType.LIST_PLAYLISTS: ["playlist", "playlists"],
                IntentType.ADD_TASK: ["add task", "new task", "todo", "to-do", "to do list", "remind me to"],
                IntentType.READ_TASKS: ["my tasks", "show tasks", "pending tasks", "task list", "show my to do"],
                IntentType.MANAGE_EXPENSES: ["spent", "expense", "income", "salary", "transfer", "balance", "owe", "owes", "debt", "lent", "borrowed", "spending", "how much"],
            }
            
            for intent_type, keywords in KEYWORD_INTENT_MAP.items():
                if any(kw in combined for kw in keywords):
                    print(f"[INTENT] Keyword fallback matched: {intent_type}")
                    return [intent_type], {}
            
            return [IntentType.CONVERSE], {}

    # OpenRouter Logic
    raw_content = None
    if OPENROUTER_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0}
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ERROR] OpenRouter failed: {e}")
        
        if not raw_content and OPENROUTER_API_KEY:
            # We had a key but no content - check if it was a non-200 response
            try:
                # Re-check response if possible or just log that we are falling back
                print(f"[INTENT] OpenRouter Diagnostic: Status {resp.status_code if 'resp' in locals() else 'Unknown'}")
                if 'resp' in locals() and resp.status_code != 200:
                    print(f"[INTENT] OpenRouter Error Body: {resp.text}")
            except:
                pass

    # Local Fallback
    if not raw_content:
        print("[INTENT] Using Local Fallback...")
        raw_content = LocalLLM.get_instance().generate(messages)

    intents, entities = process_raw_result(raw_content)
    
    # Update State
    state["current_node"] = "intent_classifier"
    state["execution_path"] = state.get("execution_path", []) + ["intent_classifier"]
    
    state["intent"] = intents[0]
    state["secondary_intents"] = intents[1:]
    state["intent_confidence"] = 0.95
    state["extracted_entities"] = entities
    
    # Context Mapping
    state["context"]["track_name"] = entities.get("track")
    state["context"]["playlist_name"] = entities.get("playlist")
    state["context"]["target_object"] = entities.get("target") or entities.get("track") or entities.get("playlist")
    state["context"]["target_device"] = entities.get("device")

    print(f"[INTENT] Classified: {state['intent']} (Secondary: {state['secondary_intents']})")
    return state
