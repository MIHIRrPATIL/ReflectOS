import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json

# Mock dependencies
sys.modules['cv2'] = MagicMock()
sys.modules['paddleocr'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain.docstore'] = MagicMock()

# Setup paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ai.graph.graph import build_graph

class TestSpotifyAgenticFlow(unittest.TestCase):
    def setUp(self):
        self.app = build_graph()

    @patch('services.spotify_service.SpotifyOAuth')
    @patch('ai.core.local_llm.LocalLLM.generate')
    @patch('requests.post')
    @patch('services.spotify_service.SpotifyService.get_instance')
    def test_spotify_multi_intent_flow(self, mock_spotify_inst, mock_requests_post, mock_llm_gen, mock_oauth):
        # 1. Mock Spotify Service Methods
        mock_sp = MagicMock()
        mock_spotify_inst.return_value = mock_sp
        mock_sp.sp = MagicMock() # Ensure .sp is not None
        
        mock_sp.get_devices.return_value = {'devices': [{'id': 'dev1', 'name': 'Living Room Speaker'}]}
        mock_sp.transfer_playback.return_value = True
        mock_sp.search.return_value = {'tracks': {'items': [{'uri': 'spotify:track:123', 'name': 'Bohemian Rhapsody', 'artists': [{'name': 'Queen'}]}]}}
        mock_sp.play.return_value = True

        # 2. Mock LocalLLM for Intent & Response if used
        def mock_llm_side_effect(messages):
            prompt = str(messages)
            if "Intent Classifier" in prompt:
                return json.dumps({
                    "intents": ["SPOTIFY_DEVICES", "SPOTIFY_PLAYBACK"],
                    "target": "Bohemian Rhapsody",
                    "target_device": "Living Room Speaker"
                })
            return "Switched to your speaker and started playing Bohemian Rhapsody!"

        mock_llm_gen.side_effect = mock_llm_side_effect

        # 3. Mock Cloud LLM (OpenRouter)
        def post_side_effect(url, headers=None, data=None, json_arg=None, timeout=None):
            import json as json_mod
            req_data = json_arg or (json_mod.loads(data) if data else {})
            prompt = str(req_data.get('messages', ''))
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            if "Intent Classifier" in prompt:
                mock_resp.json.return_value = {
                    "choices": [{"message": {"content": json_mod.dumps({
                        "intents": ["SPOTIFY_DEVICES", "SPOTIFY_PLAYBACK"],
                        "target": "Bohemian Rhapsody",
                        "target_device": "Living Room Speaker"
                    })}}]
                }
            else:
                mock_resp.json.return_value = {
                    "choices": [{"message": {"content": "I've switched playback to your Living Room Speaker and started playing Bohemian Rhapsody by Queen."}}]
                }
            return mock_resp

        # Handle patch('requests.post') which is used in nodes
        mock_requests_post.side_effect = post_side_effect

        # Initial State
        state = {
            "user_input": "Switch to Living Room Speaker and play Bohemian Rhapsody",
            "context": {"history": []},
            "interrupted": False,
            "intents": [],
            "confidence": 0.0,
            "response": None,
            "tool_outputs": {},
            "skills_history": {}
        }

        # Invoke Graph
        result = self.app.invoke(state)

        # Assertions
        print(f"\n--- Spotify Multi-Tool Test Results ---")
        print(f"User Input: {state['user_input']}")
        print(f"Final Response: {result['response']}")
        print(f"Tool Outputs Keys: {list(result['tool_outputs'].keys())}")
        
        self.assertIn("spotify_devices", result['tool_outputs'])
        self.assertIn("spotify_playback", result['tool_outputs'])
        self.assertIn("Living Room Speaker", result['response'])
        self.assertIn("Queen", result['response'])
        self.assertEqual(len(result['intents']), 0) 

if __name__ == '__main__':
    unittest.main()
