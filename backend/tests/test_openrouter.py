import requests
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
url = "https://openrouter.ai/api/v1/chat/completions"

models = [
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "xiaomi/mimo-v2-flash",
    "xiaomi/mimo-v2-flash:free",
    "mistralai/mistral-7b-instruct:free"
]

print(f"Key loaded: {key[:10]}...{key[-5:] if key else 'None'}")

for model in models:
    print(f"\n--- Testing Model: {model} ---")
    try:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 0
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Success!")
            break
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")
