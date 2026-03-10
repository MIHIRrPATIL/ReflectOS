import statistics
from utils.volume_control import set_master_volume as _set_master_volume

class VolumeSmoother:
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.buffer = []
    
    def add(self, value):
        self.buffer.append(value)
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)
            
    def get_median(self):
        if not self.buffer:
            return None
        return int(statistics.median(self.buffer))
        
    def reset(self):
        self.buffer = []

volume_smoother = VolumeSmoother(window_size=8)

def set_volume(level):
    """Adds to smoother and sets system volume if smoothed."""
    volume_smoother.add(level)
    smoothed_level = volume_smoother.get_median()
    if smoothed_level is not None:
        try:
            _set_master_volume(smoothed_level)
            return True
        except Exception as e:
            print(f"[ERROR] Volume Service: {e}")
    return False

def reset_volume_buffer():
    volume_smoother.reset()
