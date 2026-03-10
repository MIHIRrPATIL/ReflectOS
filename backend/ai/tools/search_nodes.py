import os
import requests
import json
from ai.core.state import ReflectState

def search_node(state: ReflectState):
    """
    Template node for searching the web (SEARCH_WEB).
    In a real implementation, this would use Tavily, DuckDuckGo, or Google Search API.
    """
    from services.ai_service import ai_service
    if state.get("interrupted") or ai_service.active_command_id != state.get("request_id"):
        print(f"[SEARCH] Node skipped due to interrupt (Request: {state.get('request_id')})")
        state["interrupted"] = True
        return state

    user_input = state.get("user_input", "")
    print(f"[SEARCH] Searching for: {user_input}")
    
    # 1. Gather API Keys
    keys = [
        os.getenv("TAVILY_API_KEY"),
        os.getenv("TAVILY_API_KEY_2"),
        os.getenv("TAVILY_API_KEY_3")
    ]
    # Filter out None or empty keys
    active_keys = [k for k in keys if k and k.strip()]
    
    if not active_keys:
        print("[SEARCH] Error: No Tavily API keys found in .env")
        state["tool_outputs"]["search"] = {"status": "error", "message": "No search API keys configured."}
        return state

    results = None
    last_error = None
    
    # 2. Key Rotation Fallback Logic
    for key in active_keys:
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": key,
                "query": user_input,
                "search_depth": "advanced",
                "include_answer": True,
                "max_results": 5
            }
            
            resp = requests.post(url, json=payload, timeout=15)
            
            if resp.status_code == 200:
                results = resp.json()
                print(f"[SEARCH] Successful result using key: {key[:8]}...")
                break
            elif resp.status_code == 429:
                print(f"[SEARCH] Rate limit (429) hit for key: {key[:8]}...")
                last_error = "Rate limit exceeded."
                continue
            else:
                print(f"[SEARCH] Error irc {resp.status_code}: {resp.text}")
                last_error = f"API Error {resp.status_code}"
                continue
                
        except Exception as e:
            print(f"[SEARCH] Connection error with key: {key[:8]}...: {e}")
            last_error = str(e)
            continue

    # 3. Handle Outcome
    if results:
        tool_output = {
            "status": "success",
            "query": user_input,
            "answer": results.get("answer"),
            "results": [
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": r.get("content")
                } for r in results.get("results", [])
            ],
            "summary": results.get("answer") or f"I found {len(results.get('results', []))} results for '{user_input}'."
        }
    else:
        tool_output = {
            "status": "error",
            "message": last_error or "Search failed after trying all keys."
        }
    
    # Update State
    state["tool_outputs"]["search"] = tool_output
    state["current_node"] = "search_node"
    state["execution_path"] = state.get("execution_path", []) + ["search_node"]
    
    return state
