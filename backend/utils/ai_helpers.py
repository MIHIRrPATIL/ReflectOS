import json

def extract_json(content):
    """
    Robustly extracts and parses JSON from AI responses.
    Handles markdown code blocks and leading/trailing whitespace.
    """
    if not content:
        return {}
    
    # Extract from markdown block if present
    content = str(content).strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
        
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # If it still fails, try to find the first '{' and last '}'
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(content[start:end+1])
            except:
                pass
        raise e

def parse_ai_content(content):
    """
    Robustly extracts a single string from various LangChain/Gemini content formats.
    Handles:
    - Simple string
    - List of strings
    - List of dicts (e.g. [{'type': 'text', 'text': '...'}])
    - Mixed content
    """
    if content is None:
        return ""
        
    if isinstance(content, str):
        return content
        
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # Handle OpenAI/Anthropic/Gemini style content blocks
                if 'text' in item:
                    parts.append(item['text'])
                # Fallback for other keys if needed? usually 'text' is standard for text blocks
        return " ".join(parts)
        
    # Fallback
    return str(content)
