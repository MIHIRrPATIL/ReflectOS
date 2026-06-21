import os
import requests
from tqdm import tqdm

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai", "models", "phi")
MODEL_PATH = os.path.join(MODEL_DIR, "Phi-3-mini-4k-instruct-q4.gguf")
# Using a GGUF quantized version of Phi-3
URL = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"

def download_model():
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
    
    file_size = 0
    if os.path.exists(MODEL_PATH):
        file_size = os.path.getsize(MODEL_PATH)
    
    headers = {}
    if file_size > 0:
        headers["Range"] = f"bytes={file_size}-"
        print(f"[SYSTEM] Resuming download from {file_size / (1024*1024):.2f} MB...")

    response = requests.get(URL, headers=headers, stream=True, timeout=30)
    
    if response.status_code == 416: # Range not satisfiable
        print(f"[SYSTEM] Model already exists and is complete at {MODEL_PATH}")
        return
    
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0)) + file_size
    mode = 'ab' if file_size > 0 else 'wb'

    print(f"[SYSTEM] Downloading Phi-3 model (Total: {total_size / (1024*1024*1024):.2f} GB) to {MODEL_PATH}...")
    
    try:
        with open(MODEL_PATH, mode) as f, tqdm(
            desc="Downloading",
            total=total_size,
            initial=file_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024*1024):
                f.write(data)
                bar.update(len(data))
        
        print(f"\n[SYSTEM] Model download complete: {MODEL_PATH}")
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        # Don't delete, allow resume later

if __name__ == "__main__":
    download_model()
