import sys
import subprocess
import os

# --- Platform-specific imports ---
IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform == "linux"

if IS_WINDOWS:
    try:
        import ctypes
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        import comtypes
    except ImportError:
        print("[VOLUME] pycaw/comtypes not found (Windows dependencies missing).")

def get_master_volume():
    """
    Returns the current system master volume percentage (0-100).
    """
    if IS_WINDOWS:
        try:
            comtypes.CoInitialize()
            try:
                devices = AudioUtilities.GetSpeakers()
                if hasattr(devices, 'EndpointVolume'):
                    volume = devices.EndpointVolume
                else:
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = interface.QueryInterface(IAudioEndpointVolume)
                
                scalar = volume.GetMasterVolumeLevelScalar()
                return int(round(scalar * 100))
            finally:
                comtypes.CoUninitialize()
        except Exception as e:
            print(f"Failed to get volume (Windows): {e}")
            return None
    
    elif IS_LINUX:
        try:
            # Use pactl for modern Linux (PulseAudio/PipeWire)
            result = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], capture_output=True, text=True)
            if result.returncode == 0:
                # Output looks like: "Volume: front-left: 32768 /  50% / -18.06 dB, ..."
                # We look for the first percentage.
                import re
                match = re.search(r"(\d+)%", result.stdout)
                if match:
                    return int(match.group(1))
            return None
        except Exception as e:
            print(f"Failed to get volume (Linux): {e}")
            return None
    
    return None

def set_master_volume(level_percent):
    """
    Sets the system master volume to the specified percentage (0-100).
    """
    level_percent = max(0, min(100, int(level_percent)))
    
    if IS_WINDOWS:
        try:
            # Initialize COM library for this thread
            comtypes.CoInitialize()
            try:
                devices = AudioUtilities.GetSpeakers()
                if hasattr(devices, 'EndpointVolume'):
                    volume = devices.EndpointVolume
                else:
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = interface.QueryInterface(IAudioEndpointVolume)
                
                scalar = float(level_percent) / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                print(f"System Volume Set to: {level_percent}%")
                return True
            finally:
                comtypes.CoUninitialize()
        except Exception as e:
            print(f"Failed to set volume (Windows): {e}")
            return False
            
    elif IS_LINUX:
        try:
            # Use pactl for modern Linux
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level_percent}%"], check=True)
            print(f"System Volume Set to: {level_percent}%")
            return True
        except Exception as e:
            print(f"Failed to set volume (Linux): {e}")
            return False
            
    return False
