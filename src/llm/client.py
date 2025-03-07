"""
LLM Client for Lachesis bot.

This module handles communication with the Language Model API.
"""

import asyncio
import json
import logging
import aiohttp
import backoff
from typing import Dict, Any, Optional

logger = logging.getLogger("lachesis.llm")

class LLMClient:
    """Client for interacting with LLM APIs."""
    
    def __init__(self, api_base: str, model_name: str, max_tokens: int = 1024, temperature: float = 0.7):
        """
        Initialize the LLM client.
        
        Args:
            api_base (str): Base URL for the API
            model_name (str): Name of the model to use
            max_tokens (int): Maximum number of tokens to generate
            temperature (float): Sampling temperature
        """
        self.api_base = api_base
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.session = None
    
    async def ensure_session(self):
        """Ensure an aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def generate_response(self, prompt: str, stream: bool = False) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt (str): The prompt to send to the LLM
            stream (bool): Whether to stream the response
            
        Returns:
            str: The generated text response
        """
        await self.ensure_session()
        
        # Prepare the request payload
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": stream
        }
        
        try:
            # Send the request
            async with self.session.post(
                f"{self.api_base}/completions",
                json=payload,
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"LLM API error: {response.status} - {error_text}")
                    return f"Error generating response: {response.status}"
                
                if stream:
                    # For streaming, just return the generator directly
                    return self._handle_streaming_response(response)
                else:
                    data = await response.json()
                    return data.get("choices", [{}])[0].get("text", "")
        
        except Exception as e:
            logger.error(f"Error in LLM request: {str(e)}")
            return f"Error: {str(e)}"
    
    async def _handle_streaming_response(self, response):
        """Handle a streaming response from the LLM API."""
        result = []
        async for line in response.content:
            if line:
                try:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]  # Remove 'data: ' prefix
                        if data_str != '[DONE]':
                            data = json.loads(data_str)
                            token = data.get('choices', [{}])[0].get('text', '')
                            if token:
                                result.append(token)
                                yield token
                except Exception as e:
                    logger.error(f"Error parsing streaming response: {e}")
        
        # Cannot use return with value in an async generator
        # Final yield with the complete result
        if result:
            yield ''.join(result)
            
    async def collect_streaming_response(self, streaming_gen):
        """
        Collect all tokens from a streaming response.
        
        Args:
            streaming_gen: Async generator of response tokens
            
        Returns:
            str: Complete response text
        """
        result = []
        async for token in streaming_gen:
            result.append(token)
        return ''.join(result)
    
    async def generate_function_call(self, prompt: str) -> Dict[str, Any]:
        """
        Generate a function call from the LLM.
        
        Args:
            prompt (str): The prompt to send to the LLM
            
        Returns:
            Dict: A dictionary with function name and arguments
        """
        await self.ensure_session()
        
        # Adjust the prompt to guide the model to return a function call
        function_prompt = (
            f"{prompt}\n\n"
            "Output ONLY a valid JSON object with 'name' and 'args' fields for the function call."
        )
        
        try:
            response_text = await self.generate_response(function_prompt)
            
            # Parse the JSON response
            try:
                # Extract JSON object if it's embedded in other text
                json_str = self._extract_json(response_text)
                if json_str:
                    function_call = json.loads(json_str)
                    if "name" in function_call and "args" in function_call:
                        return function_call
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse function call JSON: {response_text}")
            
            # If parsing fails, return a default response
            return {
                "name": "respond_normally",
                "args": {"text": response_text}
            }
        
        except Exception as e:
            logger.error(f"Error in function call generation: {str(e)}")
            return {
                "name": "respond_normally",
                "args": {"text": f"Error: {str(e)}"}
            }
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract a JSON object from text that might contain other content.
        
        Args:
            text (str): Text that might contain a JSON object
            
        Returns:
            Optional[str]: The extracted JSON string, or None if not found
        """
        # Try to find JSON-like content between curly braces
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # Track nesting level of curly braces to find the matching end brace
        nesting = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                nesting += 1
            elif text[i] == '}':
                nesting -= 1
                if nesting == 0:
                    # Found the matching closing brace
                    return text[start_idx:i+1]
        
        # No properly matched JSON found
        return None