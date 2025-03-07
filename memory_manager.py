# memory_manager.py

import openai # type: ignore
import re

SHORT_TERM_LIMIT = 10

class MemoryManager:
    def __init__(self):
        self.conversation_history = {}  # user_id -> list of (role, text) tuples

    def add_to_short_term(self, user_id: str, role: str, text: str):
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append((role, text))

    def get_short_term_history(self, user_id: str):
        return self.conversation_history.get(user_id, [])

    def trim_and_summarize_if_needed(self, user_id: str, profile_manager):
        """
        If history is too long, summarize older messages and put them into the user's long-term memory.
        """
        history = self.get_short_term_history(user_id)
        if len(history) > SHORT_TERM_LIMIT:
            # Summarize older messages (e.g., the first 5 messages)
            old_messages = history[:-5]
            summary = self.summarize_chat(old_messages)
            # Add summary to LTM
            profile_manager.add_long_term_memory(user_id, summary)
            # Keep the last 5 messages
            self.conversation_history[user_id] = history[-5:]

    def summarize_chat(self, messages):
        """
        Use an LLM to summarize a conversation chunk.
        """
        summarization_prompt = (
            "<|im_start|>system\n"
            "You are an expert summarizer. Convert the conversation into concise bullet points focusing on game state.\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            "Here is the conversation:\n\n"
        )
        for role, content in messages:
            summarization_prompt += f"{role.upper()}: {content}\n"
        summarization_prompt += "\n<|im_end|>\n<|im_start|>assistant\n"

        # Remember openai.api_key and openai.api_base must be set up in main
        try:
            response = openai.Completion.create(
                model="text-davinci-003",  # or your local model
                prompt=summarization_prompt,
                temperature=0.5,
                max_tokens=256,
                stop=["<|im_end|>"]
            )
            return response.choices[0].text.strip()
        except Exception as e:
            print(f"Error in summarize_chat: {e}")
            return "Unable to summarize."

    def get_relevant_memories(self, user_id: str, query_text: str, profile_manager, top_k=3):
        """
        Very naive RAG: 
        1) Get the user's facts & long_term_memories from their JSON.
        2) Rank them by overlap with the query_text.
        3) Return top_k relevant items.
        """
        profile = profile_manager.load_profile(user_id)
        facts = []  # if you have static facts for the user, you can store them in the profile
        memories = profile["long_term_memories"]

        combined = []
        for f in facts:
            combined.append(f"Fact: {f}")
        for m in memories:
            text_summary = m.get("summary", "")
            combined.append(f"Memory: {text_summary}")

        def naive_overlap_score(item: str, query: str) -> int:
            iw = set(item.lower().split())
            qw = set(query.lower().split())
            return len(iw.intersection(qw))

        scored = [(naive_overlap_score(c, query_text), c) for c in combined]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_relevant = [t for s, t in scored if s > 0][:top_k]

        return top_relevant

def remove_stage_directions(text: str) -> str:
    # For cleaning up bracketed text or asterisks
    cleaned = re.sub(r"\*[^*]+\*", "", text)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def force_lowercase_minimal(text: str) -> str:
    # Convert text to all-lowercase, remove extra punctuation if you want
    return text.lower()
