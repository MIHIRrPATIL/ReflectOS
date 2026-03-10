from ai.core.state import ReflectState
import json
import datetime
from services.calendar_service import CalendarService
from ai.core.config import OPENROUTER_API_KEY_4
from ai.core.local_llm import LocalLLM
from utils.ai_helpers import extract_json
import requests

from ai.core.config import OPENROUTER_MODEL, OPENROUTER_URL

def calendar_node(state: ReflectState):
    """
    Manages calendar events (MANAGE_CALENDAR) by connecting to Google Calendar API.
    """
    user_input = state.get("user_input", "")
    print(f"[CALENDAR] Processing: {user_input}")
    
    cal_service = CalendarService.get_instance()
    
    # 1. Parse the request to determine action and parameters
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S (%A)")  # e.g. "2026-03-01 14:19:00 (Sunday)"
    system_prompt = (
        "You are an assistant that parses calendar requests. "
        f"The current date and time is: {now_str} (timezone: Asia/Kolkata, IST, UTC+5:30). "
        "Use this to resolve relative times like 'today', 'tomorrow', 'tonight', 'this evening', etc.\n\n"
        "IMPORTANT TIME RULES:\n"
        "- If the user says a time without AM/PM (e.g. '8 o'clock', '9'), pick the NEXT occurrence that is IN THE FUTURE.\n"
        "- For example, if it is currently 2:00 PM and user says '8 o'clock', that means 8:00 PM (20:00) today, NOT 8:00 AM which already passed.\n"
        "- If user says 'morning', use 8-11 AM range. 'afternoon' = 12-5 PM. 'evening'/'tonight' = 6-10 PM.\n"
        "- Always output times in 24-hour ISO 8601 format.\n\n"
        "Determine the action required (QUERY or CREATE) and format the parameters.\n"
        "Output ONLY valid JSON, nothing else.\n"
        "For QUERY: {\"action\": \"QUERY\", \"max_results\": 5}\n"
        "For CREATE: {\"action\": \"CREATE\", \"summary\": \"Event Title\", \"start\": \"YYYY-MM-DDTHH:MM:SS\", \"end\": \"YYYY-MM-DDTHH:MM:SS\"} "
        "(Assume 1 hour duration if not specified)."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    parsed_action = None
    if OPENROUTER_API_KEY_4:
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY_4}", "Content-Type": "application/json"}
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0}
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
                parsed_action = extract_json(raw_content)
        except Exception as e:
            print(f"[ERROR] Calendar OpenRouter failed: {e}")

    if not parsed_action:
        print("[CALENDAR] Using Local Fallback for parsing...")
        raw_content = LocalLLM.get_instance().generate(messages)
        parsed_action = extract_json(raw_content)
        
    if not isinstance(parsed_action, dict):
        parsed_action = {"action": "QUERY", "max_results": 5} # Default safe fallback
        
    print(f"[CALENDAR] Parsed Action: {parsed_action}")

    # 2. Execute Action
    tool_output = {"status": "success", "action": parsed_action.get("action")}
    
    if parsed_action.get("action") == "QUERY":
        events = cal_service.get_upcoming_events(max_results=parsed_action.get("max_results", 5))
        tool_output["events"] = events
        if events:
            tool_output["message"] = f"Found {len(events)} upcoming events."
        else:
            tool_output["message"] = "No upcoming events found."
            
    elif parsed_action.get("action") == "CREATE":
        summary = parsed_action.get("summary", "New Event")
        start = parsed_action.get("start")
        end = parsed_action.get("end")
        
        if start and end:
            created = cal_service.create_event(summary, start, end)
            if created:
                tool_output["events"] = [created]
                tool_output["message"] = f"Created event: {summary}."
            else:
                tool_output["status"] = "error"
                tool_output["message"] = "Failed to create event."
        else:
            tool_output["status"] = "error"
            tool_output["message"] = "Missing start or end time for event creation."

    # Update State
    state["tool_outputs"]["calendar"] = tool_output
    state["current_node"] = "calendar_node"
    state["execution_path"] = state.get("execution_path", []) + ["calendar_node"]
    
    return state
