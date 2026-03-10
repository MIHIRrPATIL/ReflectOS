import pyttsx3
import os
import tempfile
import base64

def test_local_tts():
    print("--- [TEST] LOCAL PYTTSX3 DIAGNOSTIC ---")
    try:
        engine = pyttsx3.init()
        print(f"Engine Initialized: {engine}")
        
        voices = engine.getProperty('voices')
        print(f"Available Voices: {len(voices)}")
        for i, voice in enumerate(voices):
            print(f" - [{i}] {voice.name}")

        test_text = "This is a local TTS diagnostic test for Reflect O S."
        tmp_path = os.path.join(tempfile.gettempdir(), "test_tts_diag.mp3")
        
        print(f"Saving test audio to: {tmp_path}")
        engine.save_to_file(test_text, tmp_path)
        engine.runAndWait()
        
        if os.path.exists(tmp_path):
            size = os.path.getsize(tmp_path)
            print(f"Success! File created. Size: {size} bytes")
            os.remove(tmp_path)
        else:
            print("Error: File was not created despite runAndWait completion.")
            
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")

if __name__ == "__main__":
    test_local_tts()
