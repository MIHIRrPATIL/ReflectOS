from langgraph.graph import StateGraph, START, END
from ai.core.state import ReflectState
from core.db import db_manager

# Import Nodes
from ai.nodes.user_input import user_input_node
from ai.nodes.intent_classifier import intent_classifier_node
from ai.nodes.interrupt_handler import interrupt_handler_node
from ai.nodes.context_manager import context_manager_node
from ai.nodes.validator import validator_node # New
from ai.nodes.response_generator import response_generator_node

def build_graph():
    """
    Builds the Core Execution Spine (Phase 1) graph.
    """
    workflow = StateGraph(ReflectState)

    # Add Nodes
    workflow.add_node("user_input", user_input_node)
    workflow.add_node("interrupt_handler", interrupt_handler_node)
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("context_manager", context_manager_node)
    workflow.add_node("validator", validator_node) # New
    workflow.add_node("response_generator", response_generator_node)
    
    # Skills
    from ai.tools.weather import weather_node
    from ai.tools.vision_nodes import object_detection_node, ocr_node, outfit_analysis_node, vllm_node
    from ai.tools.youtube_nodes import youtube_node
    from ai.tools.spotify_nodes import spotify_playback_node, spotify_device_node, spotify_playlist_node, spotify_status_node
    from ai.nodes.evaluator import evaluator_node
    from ai.tools.system_control import system_control_node
    from ai.tools.calendar_nodes import calendar_node
    from ai.tools.search_nodes import search_node
    from ai.tools.task_nodes import task_node
    from ai.tools.preference_nodes import preference_node
    from ai.tools.composite_nodes import composite_node
    from ai.tools.confirmation_nodes import confirmation_node
    from ai.tools.expense_nodes import expense_node
    
    workflow.add_node("weather_node", weather_node)
    workflow.add_node("calendar_node", calendar_node)
    workflow.add_node("search_node", search_node)
    workflow.add_node("task_node", task_node)
    workflow.add_node("preference_node", preference_node)
    workflow.add_node("composite_node", composite_node)
    workflow.add_node("youtube_node", youtube_node)
    workflow.add_node("confirmation_node", confirmation_node)
    workflow.add_node("vllm_node", vllm_node)
    workflow.add_node("object_detection_node", object_detection_node)
    workflow.add_node("ocr_node", ocr_node)
    workflow.add_node("outfit_analysis_node", outfit_analysis_node)
    workflow.add_node("spotify_playback_node", spotify_playback_node)
    workflow.add_node("spotify_device_node", spotify_device_node)
    workflow.add_node("spotify_playlist_node", spotify_playlist_node)
    workflow.add_node("spotify_status_node", spotify_status_node)
    workflow.add_node("evaluator_node", evaluator_node)
    workflow.add_node("system_control_node", system_control_node)
    workflow.add_node("expense_node", expense_node)

    # ... Define Edges ...
    workflow.add_edge(START, "user_input")
    workflow.add_edge("user_input", "interrupt_handler")

    def check_interrupt(state):
        if state.get("interrupted"):
            return "response_generator" 
        return "intent_classifier"

    workflow.add_conditional_edges(
        "interrupt_handler",
        check_interrupt,
        {
            "response_generator": "response_generator",
            "intent_classifier": "intent_classifier"
        }
    )

    # Normal Flow: Classifier -> Validator -> Context Manager
    workflow.add_edge("intent_classifier", "validator")
    
    def check_validation(state):
        if state.get("validation_status") == "REJECTED":
            return "intent_classifier"
        return "context_manager"
        
    workflow.add_conditional_edges(
        "validator",
        check_validation,
        {
            "intent_classifier": "intent_classifier",
            "context_manager": "context_manager"
        }
    )
    
    skill_nodes = [
        "weather_node", "object_detection_node", "ocr_node", "outfit_analysis_node",
        "spotify_playback_node", "spotify_device_node", "spotify_playlist_node", "spotify_status_node",
        "system_control_node", "calendar_node", "search_node", "task_node",
        "preference_node", "composite_node", "confirmation_node", "expense_node"
    ]
    for node in skill_nodes + ["youtube_node"]:
        workflow.add_edge(node, "context_manager")
    
    # Final Standardizer
    workflow.add_edge("response_generator", END)

    # ROUTING LOGIC: Multi-Intent -> Evaluator
    def route_intents(state):
        from ai.core.state import IntentType
        
        # Primary intent
        intent = state.get("intent")
        
        # If we have secondary intents, we could pop them one by one, 
        # but for now let's just use the primary one.
        # Actually, the original logic was list-based. 
        # To preserve "multi-intent" execution in this flat graph:
        # we check if we have a primary intent that hasn't been executed yet.
        
        if not intent:
            return "evaluator_node"
        
        intent_map = {
            IntentType.GET_WEATHER: "weather_node",
            IntentType.GET_FORECAST: "weather_node",
            IntentType.DESCRIBE_SCENE: "vllm_node",
            IntentType.READ_TEXT: "vllm_node",
            IntentType.OUTFIT_ANALYSIS: "vllm_node",
            IntentType.PLAY_SPOTIFY: "spotify_playback_node",
            IntentType.ADD_SPOTIFY_QUEUE: "spotify_playback_node", # Combined node
            IntentType.CLEAR_SPOTIFY_QUEUE: "spotify_playback_node",
            IntentType.LIST_PLAYLISTS: "spotify_playlist_node",
            IntentType.CONTROL_SPOTIFY: "spotify_status_node",
            IntentType.SWITCH_SPOTIFY_DEVICE: "spotify_device_node",
            IntentType.SYSTEM_MEDIA_CONTROL: "system_control_node",
            IntentType.MANAGE_CALENDAR: "calendar_node",
            IntentType.SEARCH_WEB: "search_node",
            IntentType.ADD_TASK: "task_node",
            IntentType.READ_TASKS: "task_node",
            IntentType.PLAY_YOUTUBE: "youtube_node",
            IntentType.UPDATE_PREFERENCE: "preference_node",
            IntentType.COMPOSITE_TASK: "composite_node",
            IntentType.CONFIRM_ACTION: "confirmation_node",
            IntentType.MANAGE_EXPENSES: "expense_node"
        }
        
        target_node = intent_map.get(intent, "evaluator_node")
        
        # CLEAR intent after routing so we don't loop forever on the same one
        # (Legacy behavior: context_manager used to do this)
        return target_node

    def vllm_fallback_router(state):
        from ai.core.state import IntentType
        if not state.get("vllm_failed"):
            return "context_manager"
        
        # Routing to legacy nodes on failure
        intent = state.get("intent")
        if intent == IntentType.READ_TEXT:
            return "ocr_node"
        if intent == IntentType.OUTFIT_ANALYSIS:
            return "outfit_analysis_node"
        return "object_detection_node"

    workflow.add_conditional_edges(
        "vllm_node",
        vllm_fallback_router,
        {
            "context_manager": "context_manager",
            "ocr_node": "ocr_node",
            "outfit_analysis_node": "outfit_analysis_node",
            "object_detection_node": "object_detection_node"
        }
    )

    workflow.add_conditional_edges(
        "context_manager",
        route_intents,
        {
            "vllm_node": "vllm_node",
            "youtube_node": "youtube_node",
            "weather_node": "weather_node",
            "object_detection_node": "object_detection_node",
            "ocr_node": "ocr_node",
            "outfit_analysis_node": "outfit_analysis_node",
            "spotify_playback_node": "spotify_playback_node",
            "spotify_device_node": "spotify_device_node",
            "spotify_playlist_node": "spotify_playlist_node",
            "spotify_status_node": "spotify_status_node",
            "evaluator_node": "evaluator_node",
            "system_control_node": "system_control_node",
            "calendar_node": "calendar_node",
            "search_node": "search_node",
            "task_node": "task_node",
            "preference_node": "preference_node",
            "composite_node": "composite_node",
            "confirmation_node": "confirmation_node",
            "expense_node": "expense_node"
        }
    )

    def check_refinement(state):
        status = state.get("status")
        iterations = state.get("iterations", 0)
        
        if status == "REFINEMENT" and iterations <= 2:
            return "intent_classifier"
        
        return "response_generator"

    workflow.add_conditional_edges(
        "evaluator_node",
        check_refinement,
        {
            "intent_classifier": "intent_classifier",
            "response_generator": "response_generator"
        }
    )

    # Compilation with Memory
    checkpointer = db_manager.get_checkpointer()
    if checkpointer:
        print("[AI] Compiling graph with SqliteSaver checkpointer.")
        app = workflow.compile(checkpointer=checkpointer)
    else:
        print("[WARNING] Compiling graph WITHOUT checkpointer (Persistence disabled).")
        app = workflow.compile()
        
    return app
