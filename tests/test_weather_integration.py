import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from ai.graph.graph import build_graph
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

def test_weather():
    print("Building Graph...")
    app = build_graph()
    
    # Test Case 1: Weather in Mumbai
    print("\nTest Case 1: 'What is the weather in Mumbai?'")
    initial_state = {
        "user_input": "What is the weather in Mumbai?",
        "context": {},
        "interrupted": False,
        "intent": None,
        "confidence": 0.0,
        "response": None
    }
    
    result = app.invoke(initial_state)
    
    print(f"Intent: {result.get('intent')}")
    print(f"Tool Data: {result.get('tool_data')}")
    print(f"Response: {result.get('response')}")
    
    if result.get('intent') == "CHECK WEATHER" and result.get('tool_data'):
        print("Test Passed")
    else:
        print("Test Failed")

if __name__ == "__main__":
    test_weather()
