# ReflectOS Architecture Guide

ReflectOS is built on a "Hybrid Intelligence" architecture, combining cloud-scale LLMs with local, low-latency gesture and vision processing.

## Core Directories

### 🔙 Backend (`/backend`)
- **`ai/`**: The intelligence hub.
    - `nodes/`: LangGraph steps (Intent Classification, Evaluation, Response).
    - `tools/`: Actionable skills (Spotify, Weather, Expenses, Search).
    - `core/`: AI-specific configuration and local model interfaces.
- **`core/`**: System foundations (Database, Patches).
- **`services/`**: Integration layers for external APIs (Spotify, Google).
- **`utils/`**: Shared utilities like `edge-tts` and volume control.

### 🎨 Frontend (`/frontend`)
- **`lib/gesture-engine/`**: The state-of-the-art hand tracking and gesture manager.
- **`components/`**: FUI-inspired, context-aware HUD components.
- **`context/`**: State management (Zen Mode, Audio status).

## Intelligence Hierarchy
ReflectOS uses a three-tier fallback strategy:
1. **Tier 1 (Cloud)**: `meta-llama/llama-3.1-8b-instruct:free` (Fast & High Intelligence).
2. **Tier 2 (Fail-soft)**: Redundant OpenRouter keys for skill nodes.
3. **Tier 3 (Edge)**: Local `Phi-3-mini` (Private & Offline).

## Gesture Priority
Check `GestureManager.ts` for the priority chain:
1. **Safety (Fist)**: Interrupts all AI actions.
2. **Structural (Thumb Up)**: Toggles Zen Mode.
3. **Implicit (Air Tap)**: General interaction.
