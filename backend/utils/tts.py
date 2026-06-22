import base64
import tempfile
import os


def generate_tts_base64(text):
    """
    Primary: gTTS (Google Text-to-Speech — natural sounding)
    Fallback: pyttsx3 (Offline/Local)
    """
    try:
        from gtts import gTTS
        import uuid

        tmp_path = os.path.join(tempfile.gettempdir(), f"gtts_{uuid.uuid4()}.mp3")

        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(tmp_path)

        if os.path.exists(tmp_path):
            with open(tmp_path, "rb") as f:
                audio_data = f.read()
            base64_audio = base64.b64encode(audio_data).decode("utf-8")
            os.remove(tmp_path)
            print("[TTS] gTTS successful.")
            return base64_audio
    except Exception as e:
        print(f"[WARNING] gTTS failed (using fallback): {e}")

    return _generate_tts_pyttsx3_fallback(text)

def _generate_tts_pyttsx3_fallback(text):
    """
    Fallback to local pyttsx3 if gTTS fails (e.g. network/resource issues).
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
