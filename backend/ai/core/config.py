import os
from dotenv import load_dotenv

# Load .env from backend root (2 levels up from ai/core/config.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate from backend/ai/core/ to backend/
base_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
env_path = os.path.join(base_dir, ".env")

print(f"[CONFIG] Loading environment from: {env_path}")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"[CONFIG] .env loaded successfully.")
else:
    print(f"[CONFIG] WARNING: .env file not found at {env_path}")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Centralized OpenRouter model config
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions".strip()

# ── Distributed API Keys (each key has its own rate limit) ────────
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY")        # Key 1: Intent Classifier
OPENROUTER_API_KEY_2 = os.getenv("OPENROUTER_API_KEY_2")      # Key 2: Skill nodes (tasks, expenses)
OPENROUTER_API_KEY_3 = os.getenv("OPENROUTER_API_KEY_3")      # Key 3: Response Generator
OPENROUTER_API_KEY_4 = os.getenv("OPENROUTER_API_KEY_4")      # Key 4: Vision, Calendar, Composite

if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in environment variables.") 
if not SERPAPI_API_KEY:
    print("Warning: SERPAPI_API_KEY not found in environment variables.")

