import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

# Mock dependencies before imports
sys.modules['cv2'] = MagicMock()
sys.modules['paddleocr'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain.docstore'] = MagicMock()

# Setup paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ai.graph.graph import build_graph
from cv.gesture_service import gesture_service

class TestMultiToolFlow(unittest.TestCase):
    def setUp(self):
        # Build graph ensures nodes are imported
        self.app = build_graph()
        # Mock frame for vision nodes
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        gesture_service.get_latest_frame = MagicMock(return_value=mock_frame)

    @patch('ai.core.local_llm.LocalLLM.generate')
    @patch('requests.post')
    @patch('ai.graph.nodes.weather.requests.get')
    def test_weather_and_vision_flow(self, mock_weather_get, mock_requests_post, mock_llm_gen):
        # 1. Mock LocalLLM to return predictable values if used (Phi-3)
        def mock_llm_side_effect(messages):
            prompt = str(messages)
            if "Intent Classifier" in prompt:
                return '{"intents": ["CHECK WEATHER", "OBJECT_DETECTION"], "target": "bottle"}'
            if "Extract the city" in prompt:
                return "Mumbai"
            return "Local synthesis response."

        mock_llm_gen.side_effect = mock_llm_side_effect

        # 2. Mock Cloud LLM (OpenRouter) with side effects to handle both Intent and Response
        def post_side_effect(url, headers=None, data=None, json=None, timeout=None):
            import json as json_mod
            if json:
                req_data = json
            elif data:
                req_data = json_mod.loads(data)
            else:
                req_data = {}
            
            prompt = str(req_data.get('messages', ''))
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            if "Intent Classifier" in prompt:
                print("--- DEBUG: Cloud Intent Call Detected ---")
                mock_resp.json.return_value = {
                    "choices": [{"message": {"content": '{"intents": ["CHECK WEATHER", "OBJECT_DETECTION"], "target": "bottle"}'}}]
                }
            else:
                print("--- DEBUG: Cloud Synthesis Call Detected ---")
                mock_resp.json.return_value = {
                    "choices": [{"message": {"content": "I've checked the weather and scanned the room. It's a sunny 25 degrees in Mumbai, and I also noticed a bottle as you requested!"}}]
                }
            return mock_resp

        mock_requests_post.side_effect = post_side_effect

        # 3. Mock Weather API
        mock_weather_get.return_value.status_code = 200
        mock_weather_get.return_value.json.return_value = {
            "currentConditions": {"temp": 25, "conditions": "Sunny"},
            "description": "A beautiful day."
        }

        # Initial State
        state = {
            "user_input": "How is the weather and what is this bottle?",
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
        print(f"\n--- Multi-Tool Test Results ---")
        print(f"User Input: {state['user_input']}")
        print(f"Final Response: {result['response']}")
        print(f"Tool Outputs Keys: {list(result['tool_outputs'].keys())}")
        
        # Check if response is synthesized (not raw JSON)
        self.assertNotIn('{"intents"', result['response'])
        self.assertTrue(len(result['response']) > 20)
        self.assertIn("weather", result['tool_outputs'])
        self.assertIn("object_detection", result['tool_outputs'])
        self.assertEqual(len(result['intents']), 0) 

if __name__ == '__main__':
    unittest.main()
