import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils.volume_control import get_master_volume, set_master_volume

def test_volume_utils():
    print("Testing volume utilities...")
    
    current = get_master_volume()
    print(f"Current volume: {current}%")
    assert current is not None
    
    # Test setting to specific level
    test_level = (current + 5) % 100
    res = set_master_volume(test_level)
    assert res is True
    
    new_vol = get_master_volume()
    print(f"New volume: {new_vol}%")
    assert new_vol == test_level
    
    # Restore
    set_master_volume(current)
    print("✓ Volume get/set tests passed")

if __name__ == "__main__":
    test_volume_utils()
