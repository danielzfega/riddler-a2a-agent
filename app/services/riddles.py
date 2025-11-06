import os, json, re, aiohttp
from typing import Dict
from google import genai
from dotenv import load_dotenv

load_dotenv()

API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# === Gemini topic extraction ===

def get_gemini_client():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")
    return genai.Client(api_key=GEMINI_API_KEY)

async def call_gemini(prompt: str, max_tokens: int = 80) -> str:
    client = get_gemini_client()
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    config = {"temperature": 0.7, "max_output_tokens": max_tokens}

    try:
        res = client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
        if hasattr(res, "text") and res.text:
            return res.text.strip()
        return ""
    except Exception as e:
        return f"LLM ERROR: {e}"

async def extract_topic(user_text: str) -> str | None:
    """Use Gemini to extract the theme after 'about' or interpret general topic."""
    if not user_text:
        return None
    if user_text.lower().strip() in ["h", "a", "hint", "answer"]:
        return None

    # If "about ..." is present, extract manually
    m = re.search(r"about\s+([a-z\s]+)", user_text.lower())
    if m:
        return m.group(1).strip(" .,!?:;")

    # Otherwise, ask Gemini to identify the topic
    prompt = f"""
Extract the main topic from this user request: "{user_text}".
Respond with ONLY the topic word or short phrase (no extra text).
If no topic, respond with "none".
"""
    topic = await call_gemini(prompt)
    topic = topic.lower().replace('"', '').strip()
    if "none" in topic:
        return None
    return topic


# === Fetch riddles from API Ninjas ===

async def fetch_riddle_from_api(topic: str = None) -> Dict[str, str]:
    """Fetch a riddle from API Ninjas, optionally filtered by topic (via keyword search)."""
    url = "https://api.api-ninjas.com/v1/riddles"
    headers = {"X-Api-Key": API_NINJAS_KEY}
    params = {}

    # API Ninjas doesn't support topic search officially,
    # but we can filter locally after fetching
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                return {
                    "riddle": "I'm wrapped in mystery, but my source is silent. What am I?",
                    "hint": "An API error occurred.",
                    "answer": f"Error {resp.status}"
                }
            data = await resp.json()

    # Try to find one matching the topic keyword
    if topic:
        for item in data:
            if topic.lower() in item["question"].lower():
                return {
                    "riddle": item["question"],
                    "hint": f"Think about {topic}",
                    "answer": item["answer"]
                }

    # Otherwise, pick the first riddle
    if data:
        item = data[0]
        return {
            "riddle": item["question"],
            "hint": f"Consider {item['title']}",
            "answer": item["answer"]
        }

    # Fallback
    return {
        "riddle": "What disappears as soon as you say its name?",
        "hint": "Silence.",
        "answer": "Silence"
    }


# === Main generator ===

async def generate_riddle(user_text: str = None) -> Dict[str, str]:
    """Decides topic (via Gemini) and fetches riddle from API Ninjas."""
    topic = await extract_topic(user_text or "")
    return await fetch_riddle_from_api(topic)
