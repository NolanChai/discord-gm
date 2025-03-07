"""
Function dispatcher for Lachesis bot.

This module handles the registration and dispatching of functions
that can be called by the LLM.
"""

import json
import re
import logging
from typing import Dict, Any, Callable, Optional, Tuple

logger = logging.getLogger("lachesis.function_dispatcher")

class FunctionDispatcher:
    """
    Dispatches function calls from LLM responses to registered handlers.
    """
    
    def __init__(self):
        """Initialize the function dispatcher."""
        self.functions = {}
    
    def register_function(self, name: str, handler: Callable):
        """
        Register a function handler.
        
        Args:
            name (str): Name of the function
            handler (Callable): Function to call when this function is dispatched
        """
        self.functions[name] = handler
        logger.info(f"Registered function: {name}")
    
    async def dispatch(self, function_call: Dict[str, Any], **kwargs):
        """
        Dispatch a function call to the appropriate handler.
        
        Args:
            function_call (Dict): Function call with name and args
            **kwargs: Additional arguments to pass to the handler
            
        Returns:
            Any: Result of the function call
        """
        name = function_call.get("name")
        args = function_call.get("args", {})
        
        if not name:
            logger.warning("Function call missing name")
            return None
        
        if name not in self.functions:
            logger.warning(f"Unknown function: {name}")
            if "message" in kwargs:
                await kwargs["message"].channel.send(f"Sorry, I don't know how to '{name}'.")
            return None
        
        try:
            logger.info(f"Dispatching function: {name} with args: {args}")
            return await self.functions[name](**args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing function {name}: {str(e)}")
            if "message" in kwargs:
                await kwargs["message"].channel.send(f"Error executing {name}: {str(e)}")
            return None
    
    def extract_function_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract a function call from text.
        
        This handles various formats that the LLM might output, including:
        - Clean JSON: {"name": "function_name", "args": {...}}
        - JSON with backticks: ```json {"name": "function_name", "args": {...}} ```
        - Function-like syntax: function_name(arg1="value", arg2="value")
        
        Args:
            text (str): Text that might contain a function call
            
        Returns:
            Optional[Dict]: Extracted function call or None if not found
        """
        # Try to extract JSON first
        json_match = self._extract_json_object(text)
        if json_match:
            try:
                data = json.loads(json_match)
                if "name" in data and isinstance(data["name"], str):
                    if "args" not in data:
                        data["args"] = {}
                    return data
            except json.JSONDecodeError:
                pass
        
        # Try to extract function-like syntax
        func_match = re.search(r'(\w+)\s*\((.*)\)', text)
        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2)
            
            # Parse arguments
            args = {}
            
            # Handle both key=value pairs and positional arguments
            # Handle both key=value pairs and positional arguments using triple-quoted raw string
            key_value_pattern = r"""(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\d+))"""
            for match in re.finditer(key_value_pattern, args_str):
                key = match.group(1)
                # Get the first non-None group from the value alternatives
                value = next((g for g in match.groups()[1:] if g is not None), "")
                args[key] = value
            
            return {"name": func_name, "args": args}
        
        # If nothing else worked, look for specific function names in the text
        known_functions = list(self.functions.keys())
        for func in known_functions:
            if func in text.lower():
                # Found a mention of a known function
                return {"name": func, "args": {}}
        
        return None
    
    def _extract_json_object(self, text: str) -> Optional[str]:
        """
        Extract a JSON object from text.
        
        Args:
            text (str): Text that might contain a JSON object
            
        Returns:
            Optional[str]: Extracted JSON string or None if not found
        """
        # First try to find JSON within code blocks
        code_block_pattern = r'```(?:json)?\s*({\s*".*})\s*```'
        code_match = re.search(code_block_pattern, text, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        # Then try to find naked JSON objects
        json_pattern = r'({(?:[^{}]|{(?:[^{}]|{[^{}]*})*})*})'
        json_match = re.search(json_pattern, text)
        if json_match:
            return json_match.group(0)
        
        return None