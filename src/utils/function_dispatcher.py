import json
import re

# Markers for function calls in LLM output
FUNCTION_MARKER_START = "<|function_call|>"
FUNCTION_MARKER_END = "<|end_function_call|>"

class FunctionDispatcher:
    """
    Handles parsing and dispatching of function calls from LLM responses.
    """
    def __init__(self):
        """Initialize the function dispatcher."""
        self.functions = {}  # name -> function
    
    def register_function(self, name, func):
        """
        Register a function to be callable by the LLM.
        
        Args:
            name: Function name
            func: Function to call
        """
        self.functions[name] = func
    
    def extract_function_call(self, text):
        """
        Extract function call JSON from text.
        
        Args:
            text: Text to extract function call from
            
        Returns:
            dict or None: Extracted function call or None if no function call found
        """
        # Try explicit markers first
        pattern = f"{FUNCTION_MARKER_START}(.*?){FUNCTION_MARKER_END}"
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            func_text = match.group(1).strip()
            try:
                return json.loads(func_text)
            except json.JSONDecodeError:
                print(f"Invalid function call JSON: {func_text}")
                return None
        
        # Then look for JSON-like structures that may be function calls
        # This is a simple heuristic and might need tuning for your specific LLM
        json_pattern = r'(?:\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*\{.*?\}\s*\})'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            try:
                func_text = match.group(0)
                return json.loads(func_text)
            except json.JSONDecodeError:
                print(f"Invalid function call JSON: {func_text}")
                return None
        
        return None
    
    async def dispatch(self, function_call, **kwargs):
        """
        Dispatch a function call to the appropriate handler.
        
        Args:
            function_call: Function call dict with 'name' and 'args'
            **kwargs: Additional arguments to pass to the function
            
        Returns:
            Any: Result of the function call
        """
        if not function_call or not isinstance(function_call, dict):
            print("Invalid function call format")
            return None
        
        func_name = function_call.get("name")
        args = function_call.get("args", {})
        
        if not func_name or func_name not in self.functions:
            print(f"Unknown function: {func_name}")
            return None
        
        try:
            func = self.functions[func_name]
            return await func(**args, **kwargs)
        except Exception as e:
            print(f"Error dispatching function {func_name}: {e}")
            return None
    
    def get_available_functions(self):
        """
        Get a list of available functions.
        
        Returns:
            list: List of available function names
        """
        return list(self.functions.keys())
    
    def get_function_descriptions(self):
        """
        Get descriptions of available functions for LLM prompts.
        
        Returns:
            str: Formatted function descriptions
        """
        descriptions = [
            "Available functions:",
            "1. start_adventure(user_id, mentions): start a new adventure",
            "2. create_character(user_id): initiate character creation",
            "3. update_character(user_id, field, value): update character sheet",
            "4. execute_script(script_name, args): run a local script",
            "5. continue_adventure(user_id): continue the adventure",
            "6. display_profile(user_id): show character profile",
        ]
        
        return "\n".join(descriptions)
