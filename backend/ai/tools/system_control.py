import json
from ai.core.state import ReflectState
from utils.volume_control import set_master_volume
import re

def system_control_node(state: ReflectState):
    """
    Handles system-level commands like volume adjustment.
    """
    print("System Control: Node Triggered")
    user_input = state.get("user_input", "").lower()
    
    # Maintenance
    state["current_node"] = "system_control_node"
    state["execution_path"] = state.get("execution_path", []) + ["system_control_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    output = {"action": "none", "result": "pending"}

    # Volume Adjustment Logic
    if "volume" in user_input:
        from utils.volume_control import get_master_volume
        
        # Extract number
        digits = re.findall(r'\d+', user_input)
        target_val = int(digits[0]) if digits else None
        
        current_vol = get_master_volume()
        
        if "increase" in user_input or "up" in user_input:
            if current_vol is not None and target_val:
                new_vol = min(100, current_vol + target_val)
                res = set_master_volume(new_vol)
                output = {"action": "volume_increase", "by": target_val, "new_level": new_vol, "success": res}
            else:
                 output = {"action": "volume_increase", "success": False, "error": "Could not determine current volume or amount to increase."}
        elif "decrease" in user_input or "down" in user_input:
            if current_vol is not None and target_val:
                new_vol = max(0, current_vol - target_val)
                res = set_master_volume(new_vol)
                output = {"action": "volume_decrease", "by": target_val, "new_level": new_vol, "success": res}
            else:
                 output = {"action": "volume_decrease", "success": False, "error": "Could not determine current volume or amount to decrease."}
        elif target_val is not None:
            res = set_master_volume(target_val)
            output = {"action": "volume_set", "level": target_val, "success": res}
        else:
            output = {"action": "volume_set", "success": False, "error": "No volume level specified."}

    state["tool_outputs"]["system_control"] = output
    return state
