import os
import aiohttp
import json
import asyncio
import time

class LLMClient:
    """
    Client for interacting with Language Model APIs.
    """
    def __init__(self, api_base="http://localhost:1234/v1", model_name="YourModelNameHere"):
        """
        Initialize the LLM client.
        
        Args:
            api_base: API base URL
            model_name: Model name to use
        """
        self.api_base = api_base
        self.model_name = model_name
        self.api_key = os.getenv("OPENAI_API_KEY", "None")  # Not used for local LM Studio
        self.temperature = float(os.getenv("TEMPERATURE", 0.8))
        self.top_p = float(os.getenv("TOP_P", 0.95))
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.stop_strings = [os.getenv("STOP_STRINGS", "<|im_end|>")]
    
    async def generate_response(self, prompt, max_tokens=300):
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            str: Generated text response
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key != "None":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "top_p": self.top_p,
            "stop": self.stop_strings
        }
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.api_base}/completions",
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            print(f"Error from LLM API (attempt {attempt+1}/{self.max_retries}): {response.status} - {error_text}")
                            
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                                continue
                            else:
                                raise Exception(f"Error from LLM API: {response.status} - {error_text}")
                        
                        result = await response.json()
                        
                        if "choices" not in result or not result["choices"]:
                            raise Exception("Invalid response format from LLM API")
                        
                        return result["choices"][0]["text"].strip()
            
            except aiohttp.ClientError as e:
                print(f"Network error (attempt {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise Exception(f"Failed to connect to LLM API after {self.max_retries} attempts: {e}")
    
    async def summarize_text(self, text, max_tokens=100):
        """
        Summarize a piece of text.
        
        Args:
            text: The text to summarize
            max_tokens: Maximum length of summary
            
        Returns:
            str: Summary of the text
        """
        prompt = f"<|im_start|>system\nPlease summarize the following text concisely.\n<|im_end|>\n<|im_start|>user\n{text}\n<|im_end|>\n<|im_start|>assistant\n"
        return await self.generate_response(prompt, max_tokens)
    
    async def generate_character_stats(self, user_responses, max_tokens=200):
        """
        Generate character stats based on user responses.
        
        Args:
            user_responses: Dictionary of question:answer pairs from character creation
            max_tokens: Maximum length of response
            
        Returns:
            dict: Generated character stats
        """
        # Format the user responses
        responses_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in user_responses.items()])
        
        prompt = (
            "<|im_start|>system\n"
            "Based on the user's responses during character creation, generate appropriate "
            "D&D-style character stats. Respond with valid JSON that includes name, race, class, "
            "stats (strength, dexterity, constitution, intelligence, wisdom, charisma), "
            "and a brief backstory. Ensure all stats are between 8 and 18, with an emphasis on "
            "stats that match the character concept.\n"
            "<|im_end|>\n"
            f"<|im_start|>user\n{responses_text}\n<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        
        response = await self.generate_response(prompt, max_tokens)
        
        # Extract JSON
        try:
            # Try to find JSON-like content within the response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            # Clean the response to make it valid JSON
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback to a basic character if JSON parsing fails
            print(f"Failed to parse character stats JSON: {response}")
            return {
                "name": "Unknown Adventurer",
                "race": "Human",
                "class": "Fighter",
                "stats": {
                    "strength": 14,
                    "dexterity": 12,
                    "constitution": 13,
                    "intelligence": 10,
                    "wisdom": 11,
                    "charisma": 10
                },
                "backstory": "A mysterious wanderer with a forgotten past."
            }