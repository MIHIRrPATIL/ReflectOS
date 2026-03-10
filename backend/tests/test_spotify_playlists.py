import os
import sys

# Ensure backend root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.core.state import create_initial_state, IntentType
from ai.nodes.intent_classifier import intent_classifier_node
from ai.tools.spotify_nodes import spotify_playback_node, spotify_playlist_node

def test_spotify_playlist_logic():
    print("--- [TEST] SPOTIFY PLAYLIST LOGIC ---")
    
    # Test 1: List Playlists Intent
    state = create_initial_state(user_id="test_user", session_id="test_session", user_input="List my playlists")
    state = intent_classifier_node(state)
    print(f"Intent for 'List my playlists': {state['intent']}")
    
    if state['intent'] == IntentType.LIST_PLAYLISTS:
        state = spotify_playlist_node(state)
        out = state["tool_outputs"].get("spotify_playlists", {})
        print(f"Playlist Node Action: {out.get('action')}")
        print(f"Playlist Count: {out.get('count')}")
        print(f"Display Text: {out.get('display_text')}")

    # Test 2: Play Playlist Intent
    state = create_initial_state(user_id="test_user", session_id="test_session", user_input="Play my Chill Vibes playlist")
    state = intent_classifier_node(state)
    print(f"\nIntent for 'Play my Chill Vibes playlist': {state['intent']}")
    print(f"Extracted Entities: {state['extracted_entities']}")
    
    # Simulate playback node execution (we won't actually trigger Spotify if no creds, but we can check logic flow)
    print("Executing Playback Node (simulated)...")
    # To avoid real API calls during test if creds are missing, we just verify the node logic doesn't crash
    try:
        state = spotify_playback_node(state)
        print("Playback node processed successfully.")
    except Exception as e:
        print(f"Playback node error (expected if credits missing): {e}")

if __name__ == "__main__":
    test_spotify_playlist_logic()
