from typing import TypedDict, Annotated, Sequence, Optional, Literal, Any
from langgraph.graph.message import add_messages
from datetime import datetime
from enum import Enum

# ═══════════════════════════════════════════════════════════════════
# ENUMS & CORE TYPES
# ═══════════════════════════════════════════════════════════════════

class IntentType(str, Enum):
    """Core categories of user intent"""
    CONVERSE = "CONVERSE"
    UPDATE_PREFERENCE = "UPDATE_PREFERENCE"
    SEARCH_WEB = "SEARCH_WEB"
    SYSTEM_MEDIA_CONTROL = "SYSTEM_MEDIA_CONTROL"
    PLAY_SPOTIFY = "PLAY_SPOTIFY"
    CONTROL_SPOTIFY = "CONTROL_SPOTIFY"
    ADD_TASK = "ADD_TASK"
    READ_TASKS = "READ_TASKS"
    MANAGE_CALENDAR = "MANAGE_CALENDAR"
    OUTFIT_ANALYSIS = "OUTFIT_ANALYSIS"
    LIST_PLAYLISTS = "LIST_PLAYLISTS"
    GET_WEATHER = "GET_WEATHER"
    GET_FORECAST = "GET_FORECAST"
    COMPOSITE_TASK = "COMPOSITE_TASK"
    CONFIRM_ACTION = "CONFIRM_ACTION"
    # Spotify specific
    SWITCH_SPOTIFY_DEVICE = "SWITCH_SPOTIFY_DEVICE"
    ADD_SPOTIFY_QUEUE = "ADD_SPOTIFY_QUEUE"
    CLEAR_SPOTIFY_QUEUE = "CLEAR_SPOTIFY_QUEUE"
    # Vision intents
    DESCRIBE_SCENE = "DESCRIBE_SCENE"
    READ_TEXT = "READ_TEXT"
    PLAY_YOUTUBE = "PLAY_YOUTUBE"
    # Expense tracking
    MANAGE_EXPENSES = "MANAGE_EXPENSES"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_CONFIRMATION = "awaiting_confirmation"

# ═══════════════════════════════════════════════════════════════════
# MAIN STATE SCHEMA (REFACTORED FOR FEASIBILITY)
# ═══════════════════════════════════════════════════════════════════

class ReflectState(TypedDict):
    """
    Streamlined ReflectOS State for better performance and feasibility.
    Divided into 6 logical blocks instead of 18 sections.
    """
    
    # 1. CONVERSATION FLOW (Live & History)
    messages: Annotated[Sequence[dict], add_messages]
    user_input: str
    response: str
    interrupted: bool
    
    # 2. IDENTITY & SESSION
    user_id: str
    session_id: str
    thread_id: str  # user_id + session_id
    
    # 3. INTENT & ROUTING
    intent: Optional[IntentType]
    intent_confidence: float
    secondary_intents: list[IntentType]
    extracted_entities: dict[str, Any]
    
    # 4. EXECUTION METADATA
    current_node: str
    execution_path: list[str]
    execution_status: ExecutionStatus
    started_at: str
    error: Optional[dict]
    critiques: list[str]
    iterations: int
    request_id: str
    image: Optional[Any] # numpy array
    image_data: Optional[str] # base64
    input_mode: str
    
    # 5. CORE CONTEXT (Refactored to be flatter)
    context: dict[str, Any]
    """
    Consolidated context container.
    Expected keys:
    - 'recent_topics': list
    - 'user_preferences': dict
    - 'time_info': dict
    - 'history': list (legacy compatibility)
    """
    
    # 6. SKILL & TOOL DATA (Consolidated)
    tool_outputs: dict[str, Any]
    """All results from specialized tools go here (Vision, Spotify, Weather, etc.)"""
    
    skills_history: dict[str, Any]
    """Persistent history of skill usages for memory"""
    
    extra: dict[str, Any]
    """Flexible overflow for experimental features (JARVIS, Learning, etc.)"""

# ═══════════════════════════════════════════════════════════════════
# STATE INITIALIZATION HELPERS
# ═══════════════════════════════════════════════════════════════════

def create_initial_state(
    user_id: str,
    session_id: str,
    user_input: str,
    input_mode: Literal["text", "voice", "vision"] = "text",
    image_data: Optional[str] = None,
    request_id: str = "unknown"
) -> ReflectState:
    """
    Creates a streamlined fresh state for a new user interaction.
    """
    thread_id = f"{user_id}_{session_id}"
    now = datetime.now()
    
    return ReflectState(
        # 1. Flow
        messages=[{"role": "user", "content": user_input}],
        user_input=user_input,
        response="",
        interrupted=False,
        input_mode=input_mode,
        
        # 2. Identity
        user_id=user_id,
        session_id=session_id,
        thread_id=thread_id,
        request_id=request_id,
        
        # 3. Intent
        intent=None,
        intent_confidence=0.0,
        secondary_intents=[],
        extracted_entities={},
        
        # 4. Execution
        current_node="user_input",
        execution_path=["user_input"],
        execution_status=ExecutionStatus.PENDING,
        started_at=now.isoformat(),
        error=None,
        critiques=[],
        iterations=0,
        image=None,
        image_data=image_data,
        
        # 5. Core Context
        context={
            "recent_topics": [],
            "user_preferences": {},
            "time_info": {
                "time_of_day": _get_time_of_day(now.hour),
                "day_of_week": now.strftime("%A"),
                "is_work_hours": _is_work_hours(now.hour, now.weekday())
            },
            "history": []
        },
        
        # 6. Tools
        tool_outputs={},
        skills_history={},
        extra={}
    )

def _get_time_of_day(hour: int) -> str:
    if 5 <= hour < 12: return "morning"
    elif 12 <= hour < 17: return "afternoon"
    elif 17 <= hour < 21: return "evening"
    return "night"

def _is_work_hours(hour: int, day: int) -> bool:
    return day < 5 and 9 <= hour < 17