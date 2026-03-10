import sys
import os
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ai.core.state import ReflectState
from ai.tools.spotify_nodes import spotify_playback_node

def test_spotify_no_device():
    print("\n--- Testing No Active Device ---")
    state = ReflectState(
        user_input="play music",
        intents=["SPOTIFY_PLAYBACK"],
        context={"target_object": None},
        tool_outputs={}
    )
    
    with patch('services.spotify_service.SpotifyService.get_instance') as mock_get:
        mock_spotify = MagicMock()
        mock_get.return_value = mock_spotify
        mock_spotify.play.return_value = "NO_ACTIVE_DEVICE"
        
        result = spotify_playback_node(state)
        output = result["tool_outputs"]["spotify_playback"]
        print(f"Output: {output}")
        assert output["action"] == "need_device"
        assert "No active Spotify device" in output["message"]

def test_spotify_need_target():
    print("\n--- Testing Need Target (Resume Failed) ---")
    state = ReflectState(
        user_input="play music",
        intents=["SPOTIFY_PLAYBACK"],
        context={"target_object": None},
        tool_outputs={}
    )
    
    with patch('services.spotify_service.SpotifyService.get_instance') as mock_get:
        mock_spotify = MagicMock()
        mock_get.return_value = mock_spotify
        mock_spotify.play.return_value = "Player command failed: No track in queue" # Example non-device error
        
        result = spotify_playback_node(state)
        output = result["tool_outputs"]["spotify_playback"]
        print(f"Output: {output}")
        assert output["action"] == "need_target"
        assert "What should I play?" in output["message"]

def test_spotify_play_track_success():
    print("\n--- Testing Play Track Success ---")
    state = ReflectState(
        user_input="play bohemian rhapsody",
        intents=["SPOTIFY_PLAYBACK"],
        context={"target_object": "bohemian rhapsody"},
        tool_outputs={}
    )
    
    with patch('services.spotify_service.SpotifyService.get_instance') as mock_get:
        mock_spotify = MagicMock()
        mock_get.return_value = mock_spotify
        mock_spotify.search.return_value = {
            'tracks': {'items': [{'uri': 'spotify:track:123', 'name': 'Bohemian Rhapsody', 'artists': [{'name': 'Queen'}]}]}
        }
        mock_spotify.play.return_value = True
        
        result = spotify_playback_node(state)
        output = result["tool_outputs"]["spotify_playback"]
        print(f"Output: {output}")
        assert output["action"] == "play_track"
        assert output["success"] is True
        assert output["track"] == "Bohemian Rhapsody"

if __name__ == "__main__":
    try:
        test_spotify_no_device()
        test_spotify_need_target()
        test_spotify_play_track_success()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed!")
        sys.exit(1)
