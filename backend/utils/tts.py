import asyncio
import edge_tts
import base64
import tempfile
import os
import threading
import queue

# Default Voice: Microsoft Guy (Neural)
# Good options: "en-US-GuyNeural", "en-US-ChristopherNeural", "en-US-EricNeural"
VOICE = "en-US-GuyNeural" 

async def _generate_audio(text, output_file):
    communicate = edge_tts.Communicate(text, VOICE)
    # 7 seconds is plenty for a short conversational response to START saving.
    # If the network is too slow, we want to fail fast and use the local voice.
    await asyncio.wait_for(communicate.save(output_file), timeout=7)

def generate_tts_base64(text):
    """
    Primary: edge-tts (Realistic Neural Voice)
    Fallback: pyttsx3 (Offline/Local)
    """
    try:
        # edge-tts is better but requires network.
        import asyncio
        import uuid
        
        tmp_path = os.path.join(tempfile.gettempdir(), f"edge_{uuid.uuid4()}.mp3")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_generate_audio(text, tmp_path))
        finally:
            loop.close()
            
        if os.path.exists(tmp_path):
            with open(tmp_path, "rb") as f:
                audio_data = f.read()
            base64_audio = base64.b64encode(audio_data).decode("utf-8")
            os.remove(tmp_path)
            print("[TTS] edge-tts successful.")
            return base64_audio
    except Exception as e:
        print(f"[WARNING] edge-tts failed (using fallback): {e}")
        
    return _generate_tts_pyttsx3_fallback(text)

def _generate_tts_pyttsx3_fallback(text):
    """
    Fallback to local pyttsx3 if edge-tts fails (e.g. network/resource issues).
    """
    print("[TTS] Attempting pyttsx3 fallback...")
    try:
        import pyttsx3
        import uuid
        
        # Clean text from special characters that pyttsx3 might struggle with
        clean_text = "".join([c for c in text if ord(c) < 128])
        
        tmp_path = os.path.join(tempfile.gettempdir(), f"fallback_{uuid.uuid4()}.mp3")
        
        engine = pyttsx3.init()
        engine.setProperty('rate', 150) # Slower is safer for clarity
        print(f"[TTS] pyttsx3: Saving to {tmp_path}...")
        engine.save_to_file(clean_text, tmp_path)
        engine.runAndWait()
        print(f"[TTS] pyttsx3: runAndWait complete.")
        
        # Give a small buffer for file write to finalize
        import time
        time.sleep(0.5)
        
        if os.path.exists(tmp_path):
            with open(tmp_path, "rb") as f:
                audio_data = f.read()
            base64_audio = base64.b64encode(audio_data).decode("utf-8")
            os.remove(tmp_path)
            print("[TTS] pyttsx3 fallback successful.")
            return base64_audio
    except Exception as e:
        print(f"[ERROR] pyttsx3 fallback failed: {e}")
    return None
