import ctypes
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import comtypes

def get_master_volume():
    """
    Returns the current system master volume percentage (0-100).
    """
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
        print(f"Failed to get volume: {e}")
        return None

def set_master_volume(level_percent):
    """
    Sets the system master volume to the specified percentage (0-100).
    """
    try:
        # Initialize COM library for this thread
        comtypes.CoInitialize()
        
        try:
            devices = AudioUtilities.GetSpeakers()
            
            # pycaw 2025+ wrapper usage
            # The AudioDevice object exposes EndpointVolume directly
            if hasattr(devices, 'EndpointVolume'):
                volume = devices.EndpointVolume
            else:
                # Fallback for older versions or raw COM objects
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
            
            # Level comes in as 0-100, allow float
            # Convert to scalar (0.0 to 1.0)
            scalar = max(0.0, min(1.0, float(level_percent) / 100.0))
            
            volume.SetMasterVolumeLevelScalar(scalar, None)
            print(f"System Volume Set to: {int(scalar * 100)}%")
            return True
        finally:
            # Uninitialize COM library
            comtypes.CoUninitialize()
            
    except Exception as e:
        print(f"Failed to set volume: {e}")
        return False
