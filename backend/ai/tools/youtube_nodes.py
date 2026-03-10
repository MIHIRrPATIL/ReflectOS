import requests
import os
from ai.core.state import ReflectState, IntentType
from ai.core.config import SERPAPI_API_KEY

def youtube_node(state: ReflectState):
    """
    Searches YouTube via SerpAPI and returns results.
    """
    from services.ai_service import ai_service
    if state.get("interrupted") or ai_service.active_command_id != state.get("request_id"):
        print(f"[YOUTUBE] Node skipped due to interrupt (Request: {state.get('request_id')})")
        state["interrupted"] = True
        return state

    print("[YOUTUBE] Searching YouTube...")
    
    # Maintenance
    state["current_node"] = "youtube_node"
    state["execution_path"] = state.get("execution_path", []) + ["youtube_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    user_input = state.get("user_input", "")
    # Use 'track' or 'target' entities if available, otherwise fallback to raw input
    query = state.get("extracted_entities", {}).get("track") or state["context"].get("target_object") or user_input
    
    if not query:
        state["tool_outputs"]["youtube"] = {"error": "No search query provided."}
        return state

    if not SERPAPI_API_KEY:
        print("[ERROR] SERPAPI_API_KEY missing.")
        state["tool_outputs"]["youtube"] = {"error": "YouTube search unavailable (API Key missing)."}
        return state

    try:
        url = "https://serpapi.com/search"
        params = {
            "engine": "youtube",
            "search_query": query,
            "api_key": SERPAPI_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            video_results = data.get("video_results", [])
            
            # Format results for the frontend/evaluator
            results = []
            for v in video_results[:5]: # Take top 5
                results.append({
                    "title": v.get("title"),
                    "link": v.get("link"),
                    "video_id": v.get("video_id"),
                    "thumbnail": v.get("thumbnail", {}).get("static"),
                    "channel": v.get("channel", {}).get("name"),
                    "length": v.get("length")
                })
            
            state["tool_outputs"]["youtube"] = {
                "results": results,
                "query": query,
                "success": len(results) > 0
            }
            print(f"[YOUTUBE] Found {len(results)} videos for '{query}'.")
        else:
            print(f"[ERROR] SerpAPI failed: {response.status_code} - {response.text}")
            state["tool_outputs"]["youtube"] = {"error": f"Search failed (Status {response.status_code})"}
            
    except Exception as e:
        print(f"[ERROR] YouTube Search error: {e}")
        state["tool_outputs"]["youtube"] = {"error": str(e)}

    return state
