import requests
import json
from ai.core.state import ReflectState
from ai.core.config import WEATHER_API_KEY
from ai.core.local_llm import LocalLLM

def weather_node(state: ReflectState):
    """
    Weather Node:
    1. Extracts location from user_input (using LLM or simple heuristic).
    2. Calls Visual Crossing Weather API.
    3. Updates state with weather data and a summary response.
    """
    # Maintenance
    state["current_node"] = "weather_node"
    state["execution_path"] = state.get("execution_path", []) + ["weather_node"]
    
    user_input = state.get("user_input", "")
    print(f"Weather Node Triggered. Input: {user_input}")
    
    # 1. Extract Location
    # Simple heuristic fallback: "weather in [LOCATION]"
    # Optimally, we use the LLM to extract this cleanly.
    
    location = "Mumbai" # Default
    
    # Try LLM extraction
    try:
        llm = LocalLLM.get_instance()
        messages = [
            {"role": "system", "content": "Extract the city or location name from the user's request. Return ONLY the city name. If no specific location is mentioned, return 'current location'."},
            {"role": "user", "content": user_input}
        ]
        extracted = llm.generate(messages).strip()
        # Clean up
        extracted = extracted.replace(".", "").replace('"', "").replace("'", "")
        if "current location" in extracted.lower():
            location = "Mumbai" # Hardcoded default for "current" for now
        else:
            location = extracted
            
        print(f"Extracted Location: {location}")
        
    except Exception as e:
        print(f"Warning: Location extraction failed: {e}. Using default.")

    # 2. Call Weather API
    if not WEATHER_API_KEY:
        state["response"] = "I cannot check the weather because the Weather API key is missing."
        return state

    base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"

    try:
        print(f"Fetching weather for: {location}")
        request_url = f"{base_url}{location}?unitGroup=metric&key={WEATHER_API_KEY}&contentType=json"
        response = requests.get(request_url)
        response.raise_for_status()
        weather_data = response.json()
        
        # 3. Format Data
        if "tool_outputs" not in state or state["tool_outputs"] is None:
            state["tool_outputs"] = {}
        
        state["tool_outputs"]["weather"] = {
            "location": location,
            "data": weather_data
        }

        # Persistent memory
        if "skills_history" not in state or state["skills_history"] is None:
            state["skills_history"] = {}
        state["skills_history"]["weather"] = state["tool_outputs"]["weather"]
        
    except Exception as e:
        print(f"Error: Weather API Error: {e}")
        if "tool_outputs" not in state or state["tool_outputs"] is None:
            state["tool_outputs"] = {}
        state["tool_outputs"]["weather"] = {"error": str(e)}

    return state
