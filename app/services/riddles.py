import os, json, re, asyncio
from typing import Dict
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

def get_gemini_client():
    if not GEMINI_API_KEY:
        raise RuntimeError("❌ GEMINI_API_KEY missing")
    return genai.Client(api_key=GEMINI_API_KEY)


async def call_gemini(prompt: str, max_tokens: int = 200) -> str:
    client = get_gemini_client()

    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    settings = {
        "temperature": 0.9,
        "top_p": 0.92,
        "max_output_tokens": max_tokens,
    }

    try:
        r = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=settings
        )
        if hasattr(r, "text") and r.text:
            return r.text.strip()

        return ""

    except Exception as e:
        return f"LLM ERROR: {e}"


def extract_topic(text: str | None) -> str | None:
    if not text:
        return None

    text = text.lower().strip()

    # Don’t treat gameplay commands as topics
    if text in ["h", "a", "hint", "answer"]:
        return None

    # detect “about X”
    match = re.search(r"about\s+([a-zA-Z]+)", text)
    if match:
        return match.group(1)

    # fallback: take first meaningful keyword > 3 characters
    for w in text.split():
        if len(w) > 3:
            return w

    return None


async def generate_riddle(user_text: str = None) -> Dict[str, str]:
    topic = extract_topic(user_text)
    topic_text = f" about {topic}" if topic else ""

    prompt = f"""
You are Riddler, a master riddle generator.
Create ONE original riddle{topic_text}.

Rules:
• Output ONLY JSON — absolutely no extra text
• No markdown or backticks
• No line breaks inside values
• Hint = short sentence
• Answer = one word or short phrase
• Riddle must be clever, original and not a common internet riddle
• If topic provided, riddle must clearly relate to it

JSON EXACT format:
{{
 "riddle": "text",
 "hint": "text",
 "answer": "text"
}}

Example Output:
{{"riddle":"I have keys but no locks...","hint":"Used to type.","answer":"keyboard"}}

Now generate a NEW riddle.
"""

    out = await call_gemini(prompt, 200)

    match = re.search(r"\{[\s\S]*\}", out)
    if match:
        try:
            obj = json.loads(match.group(0))
            return {
                "riddle": obj.get("riddle", "").strip(),
                "hint": obj.get("hint", "").strip(),
                "answer": obj.get("answer", "").strip()
            }
        except:
            pass

    return {
        "riddle": "I speak without a mouth and hear without ears. What am I?",
        "hint": "You hear me bounce back.",
        "answer": "echo"
    }
