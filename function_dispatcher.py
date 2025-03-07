import json

FUNCTION_MARKER_START = "<|function_call|>"
FUNCTION_MARKER_END = "<|end_function_call|>"

def extract_function_call(response_text: str):
    """
    If the response contains a function call JSON (wrapped in markers),
    extract and return it as a dict. Otherwise, return None.
    """
    start = response_text.find(FUNCTION_MARKER_START)
    end = response_text.find(FUNCTION_MARKER_END)
    if start != -1 and end != -1:
        json_text = response_text[start+len(FUNCTION_MARKER_START):end].strip()
        try:
            return json.loads(json_text)
        except Exception as e:
            print(f"Error parsing function call JSON: {e}")
    return None
