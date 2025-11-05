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
    if not user_text:
        return None

    user_text = user_text.lower().strip()

    # Ignore hint/answer commands
    if user_text in ["h", "a", "hint", "answer"]:
        return None

    # ✅ Capture riddle about Egypt / riddle about ancient Egypt / give me riddle about pyramids
    m = re.search(r"(?:riddle\s+about|about)\s+([a-z\s]+)", user_text)
    if m:
        topic = m.group(1).strip(" .,!?:;")
        return topic.split()[0] if len(topic.split()) > 2 else topic  # single or simple topic

    # fallback: longest meaningful word
    words = [w for w in re.findall(r"[a-zA-Z]+", user_text) if len(w) > 3]
    return words[0] if words else None


async def generate_riddle(user_text: str = None) -> Dict[str, str]:
    topic = extract_topic(user_text)
    topic_prompt = f" themed around {topic}" if topic else ""

    prompt = f"""
You are a master riddle generator.

Create ONE original riddle{topic_prompt}.

Rules:
- Output ONLY JSON. No intro text.
- NO markdown, no backticks
- No line breaks inside JSON values
- Hint: 1 short sentence
- Answer: 1 word or short phrase
- Must be clever and original, not a known riddle
- DO NOT provide hint or answer until the user replies with H or A
- The end of the response MUST say: "Reply H for Hint or A for Answer"

JSON format:
{{
 "riddle": "...",
 "hint": "...",
 "answer": "..."
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

    return {
        "riddle": "I am heard once, yet echoed twice, living in mountains of silent ice. What am I?",
        "hint": "Nature repeats me.",
        "answer": "Echo"
    }
