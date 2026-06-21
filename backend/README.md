# ReflectOS Backend

This is the core intelligence service for ReflectOS, built with Python, LangGraph, and Flask-SocketIO.

## Structure
- **`app.py`**: Entry point for the Flask-SocketIO server.
- **`ai/`**: The LangGraph-based brain.
    - `graph/`: Defines the agentic workflow and state transitions.
    - `nodes/`: Functional steps (Intent Classifier, Evaluator, etc.).
    - `tools/`: Actionable skills (Spotify, YouTube, Weather).
    - `core/`: Configuration and Local LLM (Llama-cpp) integration.
- **`services/`**: Integration logic for Third-party APIs (Spotify, Google).
- **`utils/`**: Helper modules for Speech (TTS) and System Control.

## Intelligence Strategy
The backend operates on a **Hybrid-Cloud** model:
1. **Primary**: OpenRouter (Google Gemma 3 / Meta Llama 3).
2. **Fallback**: Local Phi-3 (GGUF) running via CPU/GPU.

## Maintenance
- **Model Check**: Run `python download_model.py` to ensure the local model is ready.
- **Dependencies**: Keep `requirements.txt` updated. Currently requires `llama-cpp-python`, `edge-tts`, and `spotipy`.
