import os
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

class LocalLLM:
    _instance = None
    _model = None
    
    # Path to model relative to backend root or absolute
    # Adjust this path based on where the file actually is: backend/ai/models/phi/Phi-3-mini-q4.gguf
    MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai", "models", "phi", "Phi-3-mini-4k-instruct-q4.gguf")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LocalLLM()
        return cls._instance

    def load_model(self):
        if self._model is None:
            if Llama is None:
                print("[ERROR] llama-cpp-python not installed. Cannot load local model.")
                return False
                
            if not os.path.exists(self.MODEL_PATH):
                 print(f"[ERROR] Local model file not found at {self.MODEL_PATH}")
                 return False

            print(f"[SYSTEM] Loading Local Phi-3 Model from {self.MODEL_PATH}...")
            try:
                # OPTIMIZATIONS:
                # n_threads: Using full core count as benchmark showed 16 > 8 for this hardware
                # n_ctx: 512 is plenty for user commands and faster to process
                threads = os.cpu_count() or 4
                
                self._model = Llama(
                    model_path=self.MODEL_PATH,
                    n_ctx=4096,
                    n_batch=128,
                    n_threads=threads,
                    n_gpu_layers=-1, # Offload to GPU if possible
                    verbose=False    # Reduce logging overhead
                )
                print(f"[SYSTEM] Local Phi-3 Model Loaded (Threads: {threads}).")
            except Exception as e:
                print(f"[ERROR] Failed to load local model: {e}")
                self._model = None
                return False
        return True

    def generate(self, messages):
        """
        Generates response using Phi-3 with low-latency settings.
        """
        if not self.load_model() or not self._model:
            return "Error: Local model could not be loaded."

        # Streamlined Prompt for Phi-3 (Avoid heavy system messages if redundant)
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                # Phi-3 likes system info as part of first user turn or specific tag
                prompt += f"<|user|>\nInstruction: {content}<|end|>\n" 
            elif role == "user":
                prompt += f"<|user|>\n{content}<|end|>\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}<|end|>\n"
        
        prompt += "<|assistant|>\n"
        
        # Safety: truncate prompt if it exceeds context window
        # Rough estimate: 1 token ≈ 4 chars for English text
        max_chars = 4096 * 3  # Leave room for generation
        if len(prompt) > max_chars:
            print(f"[LLM] WARNING: Prompt too long ({len(prompt)} chars), truncating to fit context window.")
            prompt = prompt[-max_chars:]
        
        start_time = __import__('time').time()
        
        # Generation Tweaks:
        # max_tokens=200: Capped for speed (long responses are rare for mirror)
        # temperature=0.2: More deterministic and slightly faster selection
        output = self._model(
            prompt,
            max_tokens=200,
            stop=["<|end|>", "<|user|>"],
            echo=False,
            temperature=0.2
        )
        
        duration = __import__('time').time() - start_time
        print(f"[LLM] Inference finished in {duration:.2f}s")
        
        return output['choices'][0]['text'].strip()
