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

class TestRecursiveRefinement(unittest.TestCase):
    def setUp(self):
        self.app = build_graph()

    @patch('ai.core.local_llm.LocalLLM.generate')
    @patch('requests.post')
    @patch('services.spotify_service.SpotifyService.get_instance')
    def test_spotify_refinement_loop(self, mock_spotify_inst, mock_requests_post, mock_llm_gen):
        # 1. Mock Spotify
        mock_sp = MagicMock()
        mock_spotify_inst.return_value = mock_sp
        mock_sp._ensure_sp.return_value = True
        
        # 2. Track calls to see history
        self.call_count = 0

        def post_side_effect(url, headers=None, data=None, json_arg=None, timeout=None):
            import json as json_mod
            req_data = json_arg or (json_mod.loads(data) if data else {})
            prompt = str(req_data.get('messages', ''))
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            if "Intent Classifier" in prompt:
                # Simulate refinement turn
                target = "high energy The Struts"
                if "PREVIOUS ATTEMPTS FAILED" in prompt:
                    target = "The Struts Hits"

                mock_resp.json.return_value = {
                    "choices": [{"message": {"content": json_mod.dumps({
                        "intents": ["SPOTIFY_PLAYBACK"],
                        "target": target,
                    })}}]
                }
            elif "Quality Evaluator" in prompt:
                self.call_count += 1
                if self.call_count == 1:
                    # First attempt: Fail
                    print("--- DEBUG: Evaluator triggered REFINEMENT ---")
                    mock_resp.json.return_value = {
                        "choices": [{"message": {"content": json_mod.dumps({
                            "status": "REFINEMENT",
                            "critique": "The searched results are empty. Try searching for 'The Struts Hits' instead."
                        })}}]
                    }
                else:
                    # Second attempt: Pass
                    print("--- DEBUG: Evaluator triggered SATISFACTORY ---")
                    mock_resp.json.return_value = {
                        "choices": [{"message": {"content": json_mod.dumps({
                            "status": "SATISFACTORY",
                            "critique": "Great results found."
                        })}}]
                    }
            else:
                # Synthesis
                mock_resp.json.return_value = {
                    "choices": [{"message": {"content": "I've refined my search and found the best tracks for you!"}}]
                }
            return mock_resp

        mock_requests_post.side_effect = post_side_effect

        # Mock Spotify Search Result Changes
        def mock_search_side_effect(q, type='track', limit=1):
            if "Hits" in q:
                return {'tracks': {'items': [{'uri': 'uri1', 'name': 'Could Have Been Me', 'artists': [{'name': 'The Struts'}]}]}}
            return {'tracks': {'items': []}} # First search fails
        
        mock_sp.search.side_effect = mock_search_side_effect
        mock_sp.play.return_value = True

        # Initial State
        state = {
            "user_input": "Play some high energy songs by The Struts",
            "context": {"history": []},
            "interrupted": False,
            "intents": [],
            "confidence": 0.0,
            "response": None,
            "tool_outputs": {},
            "skills_history": {},
            "iterations": 0,
            "critiques": []
        }

        # Invoke Graph
        result = self.app.invoke(state)

        # Assertions
        print(f"\n--- Recursive Refinement Test Results ---")
        print(f"Iterations: {result['iterations']}")
        print(f"Critiques: {result['critiques']}")
        print(f"Final Response: {result['response']}")
        
        self.assertEqual(result['iterations'], 1)
        self.assertEqual(len(result['critiques']), 1)
        self.assertIn("Could Have Been Me", str(result['tool_outputs']))
        self.assertIn("refined my search", result['response'])

if __name__ == '__main__':
    unittest.main()
