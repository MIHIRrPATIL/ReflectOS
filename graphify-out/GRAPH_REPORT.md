# Graph Report - .  (2026-05-01)

## Corpus Check
- Corpus is ~37,242 words - fits in a single context window. You may not need a graph.

## Summary
- 459 nodes · 632 edges · 21 communities detected
- Extraction: 70% EXTRACTED · 30% INFERRED · 0% AMBIGUOUS · INFERRED: 188 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_AI Core Nodes|AI Core Nodes]]
- [[_COMMUNITY_AI Tools Routes|AI Tools Routes]]
- [[_COMMUNITY_Expense Management|Expense Management]]
- [[_COMMUNITY_One-Hand Gestures|One-Hand Gestures]]
- [[_COMMUNITY_Two-Hand Gestures|Two-Hand Gestures]]
- [[_COMMUNITY_AI Graph Tests|AI Graph Tests]]
- [[_COMMUNITY_App Multiplexing|App Multiplexing]]
- [[_COMMUNITY_Evaluation Responses|Evaluation Responses]]
- [[_COMMUNITY_Task Services|Task Services]]
- [[_COMMUNITY_Spotify Intents|Spotify Intents]]
- [[_COMMUNITY_TTS Interrupts|TTS Interrupts]]
- [[_COMMUNITY_Calendar Service|Calendar Service]]
- [[_COMMUNITY_Volume Control|Volume Control]]
- [[_COMMUNITY_Gesture Sockets|Gesture Sockets]]
- [[_COMMUNITY_OCR Text Detection|OCR Text Detection]]
- [[_COMMUNITY_Database Core|Database Core]]
- [[_COMMUNITY_Gesture Feedback UI|Gesture Feedback UI]]
- [[_COMMUNITY_Outfit Detection|Outfit Detection]]
- [[_COMMUNITY_Task Scheduler|Task Scheduler]]
- [[_COMMUNITY_Confirmation Nodes|Confirmation Nodes]]
- [[_COMMUNITY_Core Patches|Core Patches]]

## God Nodes (most connected - your core abstractions)
1. `ReflectState` - 33 edges
2. `SpotifyService` - 26 edges
3. `ExpenseService` - 24 edges
4. `LocalLLM` - 22 edges
5. `IntentType` - 18 edges
6. `OCRHandler` - 13 edges
7. `AIService` - 12 edges
8. `ObjectDetector` - 12 edges
9. `TaskService` - 11 edges
10. `extract_json()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `test_weather()` --calls--> `build_graph()`  [INFERRED]
  tests/test_weather_integration.py → backend/ai/graph/graph.py
- `test_vision_skills()` --calls--> `build_graph()`  [INFERRED]
  tests/test_vision_integration.py → backend/ai/graph/graph.py
- `Handles system-level commands like volume adjustment.` --uses--> `ReflectState`  [INFERRED]
  backend/ai/tools/system_control.py → backend/ai/core/state.py
- `Template node for searching the web (SEARCH_WEB).     In a real implementation,` --uses--> `ReflectState`  [INFERRED]
  backend/ai/tools/search_nodes.py → backend/ai/core/state.py
- `Template node for confirming user actions (CONFIRM_ACTION).     Handles 'Yes', '` --uses--> `ReflectState`  [INFERRED]
  backend/ai/tools/confirmation_nodes.py → backend/ai/core/state.py

## Communities

### Community 0 - "AI Core Nodes"
Cohesion: 0.06
Nodes (47): get_instance(), LocalLLM, Generates response using Phi-3 with low-latency settings., create_initial_state(), ExecutionStatus, _get_time_of_day(), IntentType, _is_work_hours() (+39 more)

### Community 1 - "AI Tools Routes"
Cohesion: 0.08
Nodes (20): detect_objects(), ocr_full(), ocr_item(), get_status(), next_track(), pause_playback(), previous_track(), Skip to the next track without triggering the AI pipeline. (+12 more)

### Community 2 - "Expense Management"
Cohesion: 0.07
Nodes (26): get_balances(), get_categories(), get_debts(), get_recent(), get_summary(), Get recent transactions with optional filters., Get spending summary., Get outstanding debts with optional person filter. (+18 more)

### Community 3 - "One-Hand Gestures"
Cohesion: 0.06
Nodes (17): distance(), AirTap, CursorMove, detect(), FistMove, GunTap, MenuWheel, ModeSwitch (+9 more)

### Community 4 - "Two-Hand Gestures"
Cohesion: 0.1
Nodes (11): HandTracker, crossProduct(), distance2D(), normalize(), subtract(), AirFrame, AirMeasure, CurtainOpen (+3 more)

### Community 5 - "AI Graph Tests"
Cohesion: 0.09
Nodes (9): build_graph(), test_memory_system(), TestMultiToolFlow, test_spotify_refinement_loop(), TestRecursiveRefinement, TestSpotifyAgenticFlow, RecursiveCharacterTextSplitter, test_vision_skills() (+1 more)

### Community 6 - "App Multiplexing"
Cohesion: 0.13
Nodes (7): handle_multiplexed_message(), Unified entry point for all WebSocket messages.     Delegates to appropriate ser, GestureManager, Adds to smoother and sets system volume if smoothed., reset_volume_buffer(), set_volume(), VolumeSmoother

### Community 7 - "Evaluation Responses"
Cohesion: 0.11
Nodes (11): evaluator_node(), response_generator_node(), validator_node(), test_extract_json(), calendar_node(), expense_node(), task_node(), extract_json() (+3 more)

### Community 8 - "Task Services"
Cohesion: 0.16
Nodes (8): Update a task's title or deadline., Find a task by ID or fuzzy title match. Returns the raw row or None., Add a new task. Returns the created task dict., List tasks for a user. By default only pending tasks., Mark a task as done by ID or by fuzzy title match., Mark all pending tasks as done for a user. Returns count of tasks marked., Delete a task by ID or by fuzzy title match., TaskService

### Community 9 - "Spotify Intents"
Cohesion: 0.14
Nodes (13): intent_classifier_node(), test_spotify_need_target(), test_spotify_no_device(), test_spotify_play_track_success(), test_spotify_playlist_logic(), Handles device listing and switching., Handles playlist discovery and creation., Retrieves current track info and status. (+5 more)

### Community 10 - "TTS Interrupts"
Cohesion: 0.2
Nodes (7): AIService, get_instance(), _generate_audio(), generate_tts_base64(), _generate_tts_pyttsx3_fallback(), Primary: edge-tts (Realistic Neural Voice)     Fallback: pyttsx3 (Offline/Local), Fallback to local pyttsx3 if edge-tts fails (e.g. network/resource issues).

### Community 11 - "Calendar Service"
Cohesion: 0.22
Nodes (4): CalendarService, Authenticates the user and creates the Calendar service object., Fetches upcoming events from the user's primary calendar., Creates a new event on the user's primary calendar.

### Community 12 - "Volume Control"
Cohesion: 0.24
Nodes (7): test_volume_utils(), Handles system-level commands like volume adjustment., system_control_node(), get_master_volume(), Returns the current system master volume percentage (0-100)., Sets the system master volume to the specified percentage (0-100)., set_master_volume()

### Community 13 - "Gesture Sockets"
Cohesion: 0.29
Nodes (1): GestureSocket

### Community 14 - "OCR Text Detection"
Cohesion: 0.29
Nodes (3): Detects text in the given CV2 frame (BGR).         Returns a list of results: [[, Draws bounding boxes and text on the frame., TextDetector

### Community 15 - "Database Core"
Cohesion: 0.4
Nodes (2): DatabaseManager, get_instance()

### Community 16 - "Gesture Feedback UI"
Cohesion: 0.4
Nodes (2): checkClickable(), handleGesture()

### Community 18 - "Outfit Detection"
Cohesion: 0.4
Nodes (3): analyze_outfit(), Placeholder for outfit analysis model.     Returns a list of suggestion dictiona, detect_outfit()

### Community 20 - "Task Scheduler"
Cohesion: 0.5
Nodes (1): Scheduler

### Community 22 - "Confirmation Nodes"
Cohesion: 0.67
Nodes (2): confirmation_node(), Template node for confirming user actions (CONFIRM_ACTION).     Handles 'Yes', '

### Community 23 - "Core Patches"
Cohesion: 0.67
Nodes (2): apply_patches(), Applies monkeypatches for Eventlet (if present), PaddleOCR and LangChain compati

## Knowledge Gaps
- **45 isolated node(s):** `Unified entry point for all WebSocket messages.     Delegates to appropriate ser`, `Generates response using Phi-3 with low-latency settings.`, `Core categories of user intent`, `Streamlined ReflectOS State for better performance and feasibility.     Divided`, `Creates a streamlined fresh state for a new user interaction.` (+40 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Gesture Sockets`** (10 nodes): `GestureSocket.ts`, `GestureSocket`, `.constructor()`, `.emitMessage()`, `.getInstance()`, `.getSocket()`, `.sendGesture()`, `.sendInterrupt()`, `.sendMenuAction()`, `.sendVoiceCommand()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Database Core`** (6 nodes): `db.py`, `DatabaseManager`, `.get_checkpointer()`, `.get_redis()`, `.__init__()`, `get_instance()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Gesture Feedback UI`** (6 nodes): `checkClickable()`, `fetchStatus()`, `handleGesture()`, `handleMessage()`, `spotifyControl()`, `GestureFeedback.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Task Scheduler`** (4 nodes): `scheduler.py`, `Scheduler`, `.__init__()`, `.schedule_task()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Confirmation Nodes`** (3 nodes): `confirmation_nodes.py`, `confirmation_node()`, `Template node for confirming user actions (CONFIRM_ACTION).     Handles 'Yes', '`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Core Patches`** (3 nodes): `patches.py`, `apply_patches()`, `Applies monkeypatches for Eventlet (if present), PaddleOCR and LangChain compati`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReflectState` connect `AI Core Nodes` to `AI Tools Routes`, `Volume Control`, `Confirmation Nodes`, `Spotify Intents`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `ExpenseService` connect `Expense Management` to `AI Core Nodes`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `Manages expenses, income, transfers, debts, and financial summaries.     Uses LL` connect `AI Core Nodes` to `Expense Management`, `Evaluation Responses`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `str` (e.g. with `object_detection_node()` and `ocr_node()`) actually correct?**
  _`str` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `ReflectState` (e.g. with `Manages expenses, income, transfers, debts, and financial summaries.     Uses LL` and `Sends base64 image data to a VLM (Vision-Language Model) via OpenRouter.`) actually correct?**
  _`ReflectState` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `SpotifyService` (e.g. with `Handles core playback: search, play, pause, skip, volume.` and `Handles device listing and switching.`) actually correct?**
  _`SpotifyService` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ExpenseService` (e.g. with `Manages expenses, income, transfers, debts, and financial summaries.     Uses LL` and `Get all account balances.`) actually correct?**
  _`ExpenseService` has 6 INFERRED edges - model-reasoned connections that need verification._