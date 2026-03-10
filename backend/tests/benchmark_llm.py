from ai.core.local_llm import LocalLLM
import time

def benchmark():
    llm = LocalLLM.get_instance()
    print("Checking model loading...")
    
    start_load = time.time()
    loaded = llm.load_model()
    load_time = time.time() - start_load
    
    print(f"Model Loaded: {loaded}")
    print(f"Load Time: {load_time:.2f}s")
    
    if not loaded:
        return

    # Test prompt
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain what a magic mirror is in one sentence."}
    ]
    
    print("\nStarting generation benchmark...")
    start_gen = time.time()
    response = llm.generate(messages)
    gen_time = time.time() - start_gen
    
    print(f"\nResponse: {response}")
    print(f"Total Generation Time: {gen_time:.2f}s")
    
    # We can't easily get token count without access to the internal llama instance
    # but we can see the logs if we run this.
    
if __name__ == "__main__":
    benchmark()
