import os
from dotenv import load_dotenv

# Load .env from backend root (2 levels up from ai/core/config.py)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Centralized OpenRouter model config
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "stepfun/step-3.5-flash:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Distributed API Keys (each key has its own rate limit) ────────
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY")        # Key 1: Intent Classifier
OPENROUTER_API_KEY_2 = os.getenv("OPENROUTER_API_KEY_2")      # Key 2: Skill nodes (tasks, expenses)
OPENROUTER_API_KEY_3 = os.getenv("OPENROUTER_API_KEY_3")      # Key 3: Response Generator
OPENROUTER_API_KEY_4 = os.getenv("OPENROUTER_API_KEY_4")      # Key 4: Vision, Calendar, Composite

if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in environment variables.")
if not SERPAPI_API_KEY:
    print("Warning: SERPAPI_API_KEY not found in environment variables.")

