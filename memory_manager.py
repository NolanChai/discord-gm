import openai
import re

SHORT_TERM_LIMIT = 10

class MemoryManager:
    def __init__(self):
        self.conversation_history = {}  # user_id -> list of (role, text)

    def add_to_short_term(self, user_id: str, role: str, text: str):
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append((role, text))

    def get_short_term_history(self, user_id: str):
        return self.conversation_history.get(user_id, [])

    def trim_and_summarize_if_needed(self, user_id: str, profile_manager):
        history = self.get_short_term_history(user_id)
        if len(history) > SHORT_TERM_LIMIT:
            old_messages = history[:-5]
            summary = self.summarize_chat(old_messages)
            profile_manager.add_long_term_memory(user_id, summary)
            self.conversation_history[user_id] = history[-5:]

    def summarize_chat(self, messages):
        summarization_prompt = (
            "<|im_start|>system\n"
            "Summarize the following conversation into concise bullet points about game state:\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            "Conversation:\n"
        )
        for role, content in messages:
            summarization_prompt += f"{role.upper()}: {content}\n"
        summarization_prompt += "<|im_end|>\n<|im_start|>assistant\n"
        try:
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=summarization_prompt,
                temperature=0.5,
                max_tokens=256,
                stop=["<|im_end|>"]
            )
            return response.choices[0].text.strip()
        except Exception as e:
            print(f"Summarization error: {e}")
            return "Unable to summarize."

def remove_stage_directions(text: str) -> str:
    cleaned = re.sub(r"\*[^*]+\*", "", text)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def force_lowercase_minimal(text: str) -> str:
    return text.lower()
