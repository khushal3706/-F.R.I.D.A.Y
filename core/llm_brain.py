"""
╔══════════════════════════════════════════════════════════════╗
║       FRIDAY — LLM Brain (core/llm_brain.py)                ║
║  FREE STACK: Google Gemini 1.5 Flash | Ollama (local)       ║
║  Uses google-genai SDK (new, actively maintained)           ║
║  Free tier: 15 RPM, 1 million tokens/day                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import re
from core.logger import get_logger
from config import (
    LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    SYSTEM_PROMPT, AGENT_HISTORY_LIMIT,
)

log = get_logger("LLMBrain")


# ─────────────────────────────────────────────────────────────
# ▸ CONVERSATION MEMORY
# ─────────────────────────────────────────────────────────────
class Memory:
    """Rolling conversation buffer — keeps last `limit` turn pairs."""

    def __init__(self, limit: int = AGENT_HISTORY_LIMIT):
        self._history: list[dict] = []
        self.limit = limit

    def add(self, role: str, content: str):
        self._history.append({"role": role, "content": content})
        if len(self._history) > self.limit * 2:
            self._history = self._history[-(self.limit * 2):]

    def get_messages(self, system_prompt: str = SYSTEM_PROMPT) -> list[dict]:
        """Full message list including system prompt (for Ollama / generic)."""
        return [{"role": "system", "content": system_prompt}] + self._history

    def get_gemini_contents(self) -> list[dict]:
        """
        History formatted for the google-genai SDK.
        Roles must be 'user' or 'model' (not 'assistant').
        """
        contents = []
        for msg in self._history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        return contents

    def clear(self):
        self._history.clear()
        log.info("Conversation memory cleared.")

    def __len__(self):
        return len(self._history)


# ─────────────────────────────────────────────────────────────
# ▸ GEMINI BACKEND  (google-genai — new SDK, actively supported)
# ─────────────────────────────────────────────────────────────
def _call_gemini(messages: list[dict]) -> str:
    """
    Call Gemini 1.5 Flash using the new google-genai SDK.
    Free tier: 15 RPM / 1 million tokens per day.
    Get key: https://aistudio.google.com/apikey
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("Run: pip install google-genai")

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY not set!\n"
            "  1. Visit https://aistudio.google.com/apikey\n"
            "  2. Create a free API key\n"
            "  3. Add to .env:  GEMINI_API_KEY=your_key_here"
        )

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Separate system message from chat history
    chat_msgs = [m for m in messages if m["role"] != "system"]

    # Build contents list for the API — all but last message become history
    contents = []
    for msg in chat_msgs:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=msg["content"])]
        ))

    log.debug(f"Gemini request → model={GEMINI_MODEL}, turns={len(contents)}")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )
    return response.text.strip()


# ─────────────────────────────────────────────────────────────
# ▸ OLLAMA BACKEND  (local, fully offline)
# ─────────────────────────────────────────────────────────────
def _call_ollama(messages: list[dict]) -> str:
    """
    Call a local Ollama model via REST API.
    Install: https://ollama.com  →  ollama pull llama3
    """
    try:
        import httpx
    except ImportError:
        raise ImportError("Run: pip install httpx")

    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    log.debug(f"Ollama request → model={OLLAMA_MODEL}")
    response = httpx.post(url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


# ─────────────────────────────────────────────────────────────
# ▸ CODE EXTRACTION
# ─────────────────────────────────────────────────────────────
def extract_code_block(text: str) -> str | None:
    """Extract the first ```python ... ``` code block from model output."""
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        log.debug(f"Extracted code block ({len(code)} chars).")
        return code
    return None


# ─────────────────────────────────────────────────────────────
# ▸ MAIN BRAIN CLASS
# ─────────────────────────────────────────────────────────────
class FridayBrain:
    """
    Central reasoning engine for FRIDAY.

    Usage:
        brain = FridayBrain()
        reply, code = brain.think("open Chrome and search for AI news")
    """

    def __init__(self, provider: str | None = None):
        self.provider = (provider or LLM_PROVIDER).lower()
        self.memory   = Memory()
        log.info(f"FridayBrain ready — provider: {self.provider.upper()}")

    def _call_llm(self, messages: list[dict]) -> str:
        if self.provider == "gemini":
            return _call_gemini(messages)
        elif self.provider == "ollama":
            return _call_ollama(messages)
        else:
            raise ValueError(
                f"Unknown LLM provider: {self.provider!r}\n"
                "  Options: 'gemini' (free) | 'ollama' (local)"
            )

    def think(self, user_input: str, extra_context: str = "") -> tuple[str, str | None]:
        """
        Process a user command and return (reply_text, python_code | None).

        Args:
            user_input    : Raw command / question from the user.
            extra_context : Extra context to prepend (search results, OCR, etc).
        """
        full_input = user_input
        if extra_context:
            full_input = f"[Context]\n{extra_context}\n\n[User Request]\n{user_input}"

        self.memory.add("user", full_input)
        messages = self.memory.get_messages()

        log.info(f"Thinking … (memory={len(self.memory)} turns, provider={self.provider.upper()})")
        try:
            reply = self._call_llm(messages)
        except Exception as exc:
            log.error(f"LLM call failed: {exc}")
            reply = f"[ERROR] LLM unavailable:\n{exc}"

        self.memory.add("assistant", reply)
        code = extract_code_block(reply)
        if code:
            log.info("Model returned executable code.")

        return reply, code

    def inject_context(self, context: str):
        """Push extra context (tool output, errors) into memory."""
        self.memory.add("user", f"[System Context Update]\n{context}")
        self.memory.add("assistant", "Understood. Context updated.")

    def reset(self):
        """Clear all conversation memory."""
        self.memory.clear()
