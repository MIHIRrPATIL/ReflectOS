import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils.ai_helpers import extract_json
import json

def test_extract_json():
    print("Running extract_json tests...")
    
    # Test case 1: Raw JSON
    raw = '{"status": "SATISFACTORY", "critique": ""}'
    assert extract_json(raw) == {"status": "SATISFACTORY", "critique": ""}
    print("✓ Raw JSON passed")

    # Test case 2: Markdown JSON
    md = '```json\n{"status": "REFINEMENT", "critique": "test"}\n```'
    assert extract_json(md) == {"status": "REFINEMENT", "critique": "test"}
    print("✓ Markdown JSON passed")

    # Test case 3: JSON with noise
    noise = 'Here is the result:\n```\n{"key": "value"}\n```\nHope this helps!'
    assert extract_json(noise) == {"key": "value"}
    print("✓ JSON with noise passed")

    # Test case 4: Malformed JSON with valid part
    malformed = 'Random text {"status": "OK"} more text'
    assert extract_json(malformed) == {"status": "OK"}
    print("✓ Malformed JSON with valid part passed")

    print("\nAll tests passed!")

if __name__ == "__main__":
    test_extract_json()
