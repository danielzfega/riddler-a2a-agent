import os, json, re, asyncio
from typing import Dict
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

def get_gemini_client():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")
    return genai.Client(api_key=GEMINI_API_KEY)


async def call_gemini(prompt: str, max_tokens: int = 250) -> str:
    client = get_gemini_client()

    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    config = {
        "temperature": 0.9,
        "max_output_tokens": max_tokens
    }

    try:
        res = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config
        )
        if hasattr(res, "text") and res.text:
            return res.text.strip()
        return ""
    except Exception as e:
        return f"LLM ERROR: {e}"


def extract_topic(user_text: str) -> str | None:
    """Extract topic after 'about' keyword if present."""
    if not user_text:
        return None

    user_text = user_text.lower().strip()

    # Ignore hint/answer commands
    if user_text in ["h", "a", "hint", "answer"]:
        return None

    # Match "riddle about X", "give me a riddle about X", etc.
    m = re.search(r"(?:riddle\s+about|about)\s+([a-z\s]+)", user_text)
    if m:
        topic = m.group(1).strip(" .,!?:;")
        return topic

    # fallback: single long word
    words = [w for w in re.findall(r"[a-zA-Z]+", user_text) if len(w) > 3]
    return words[0] if words else None


async def generate_riddle(user_text: str = None) -> Dict[str, str]:
    """Generate riddle (with hint + answer) optionally themed by topic."""
    topic = extract_topic(user_text)
    topic_prompt = f" about {topic}" if topic else ""

    prompt = f"""
You are a creative master of riddles.

Write ONE original riddle{topic_prompt}. Provide its hint and answer.

Rules:
- Return JSON only, no markdown or backticks.
- No extra commentary or text.
- Hint: one concise clue.
- Answer: one or two words.

JSON format:
{{
 "riddle": "string",
 "hint": "string",
 "answer": "string"
}}
"""

    output = await call_gemini(prompt)

    match = re.search(r"\{.*\}", output, re.S)
    if match:
        try:
            data = json.loads(match.group(0))
            return {k: data.get(k, "").strip() for k in ["riddle", "hint", "answer"]}
        except:
            pass

    # fallback
    return {
        "riddle": "I am heard once, yet echoed twice, living in mountains of silent ice. What am I?",
        "hint": "Nature repeats me.",
        "answer": "Echo"
    }
