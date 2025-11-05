import os
import json
import re
import asyncio
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

async def call_gemini(prompt: str, max_tokens: int = 200) -> str:
    client = get_gemini_client()

    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    config_settings = {
        "temperature": 0.9,
        "max_output_tokens": max_tokens
    }

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config_settings
        )

        if hasattr(response, "text") and response.text:
            return response.text.strip()
        return ""

    except Exception as e:
        return f"LLM ERROR: {type(e).__name__}: {str(e)}"


async def generate_riddle(user_input: str = None) -> Dict[str, str]:
    """
    Generates a riddle optionally tailored to a topic detected from user input.
    """

    topic = ""
    if user_input:
        words = user_input.lower().split()
        keyword = [w for w in words if len(w) > 3][:1]  # extract 1 meaningful word
        if keyword:
            topic = f" about {keyword[0]}"

    prompt = f"""
You are a riddle generator AI. Your job is to output riddles only in valid JSON.

Create ONE original riddle{topic}.
Detect if the user's message contains a topic keyword and tailor the riddle to it.

🔒 STRICT RULES:
- Return ONLY valid JSON (NO extra text, NO markdown, NO explanation)
- Make it clever and moderately challenging
- "hint" MUST be one short sentence
- "answer" MUST be one word or short phrase

JSON format to return:

{{
 "riddle": "...",
 "hint": "...",
 "answer": "..."
}}

Example:
{{"riddle":"I have keys but open no doors; I make sound but have no voice.","hint":"You press me to make music.","answer":"piano"}}

Now generate a NEW one.
"""

    out = await call_gemini(prompt, max_tokens=200)

    # Extract JSON from output
    match = re.search(r"\{[\s\S]*\}", out)
    if match:
        try:
            obj = json.loads(match.group(0))
            return {
                "riddle": obj.get("riddle", "").strip(),
                "hint": obj.get("hint", "").strip(),
                "answer": obj.get("answer", "").strip()
            }
        except json.JSONDecodeError:
            pass

    # Fallback
    return {"riddle": "I speak without a mouth and hear without ears. What am I?",
            "hint": "It is a phenomenon, not a creature.",
            "answer": "echo"}

# import os
# import json
# import re
# import asyncio
# from typing import Dict
# from google import genai
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Environment Vars
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


# # Gemini Client
# def get_gemini_client():
#     if not GEMINI_API_KEY:
#         raise RuntimeError("GEMINI_API_KEY is missing")
#     return genai.Client(api_key=GEMINI_API_KEY)

# _store_lock = asyncio.Lock()

# # ✅ Gemini call
# # ✅ Gemini call (accept max_tokens for compatibility, ignore internally)
# # app/services/riddles.py

# # ✅ Gemini call
# # ✅ Correct Gemini call for google-genai client
# # app/services/riddles.py - Corrected version

# # ... (imports and get_gemini_client remain the same)

# # ✅ Corrected Gemini call for google-genai client
# async def call_gemini(prompt: str, max_tokens: int = None) -> str:
#     client = get_gemini_client()

#     # The prompt content needs to be in the correct list format for the SDK
#     contents = [{"role": "user", "parts": [{"text": prompt}]}]
    
#     # Configuration should use the 'config' keyword
#     config_settings = {
#         "temperature": 0.95,
#         "max_output_tokens": max_tokens or 256,
#     }

#     try:
#         response = client.models.generate_content(
#             model=GEMINI_MODEL,
#             contents=contents, # Use the list of content parts
#             config=config_settings # Use 'config' instead of 'generation_config'
#         )

#         # Extract text from Gemini response (Simplified extraction based on common SDK behavior)
#         if hasattr(response, "text") and response.text:
#             return response.text.strip()
            
#         return ""

#     except Exception as e:
#         # A more robust error message, including the error type
#         return f"LLM ERROR: {type(e).__name__}: {str(e)}"


# # ✅ Riddle generator
# # app/services/riddles.py

# # ✅ Riddle generator

# async def generate_riddle(topic: str = None) -> Dict[str, str]:
#     topic_text = f" about {topic}" if topic else ""
#     prompt = f"""
# Create one original riddle{topic_text}.
# Return ONLY valid JSON in this exact structure:
# {{
#  "riddle": "...",
#  "hint": "...",
#  "answer": "..."
# }}

# Rules:
# - Make it moderately challenging
# - No repeated famous riddles
# - Hint must be one short sentence
# - Answer one word or short phrase
# - No markdown, no backticks

# Example:
# {{"riddle":"I have keys but no locks...","hint":"You'll find me where letters live.","answer":"keyboard"}}

# Now create a new one.
# """

#     out = await call_gemini(prompt, max_tokens=200)

#     # Extract JSON from LLM output
#     m = re.search(r"(\{[\s\S]*\})", out)
#     if m:
#         try:
#             data = json.loads(m.group(1))
#             return {
#                 "riddle": data.get("riddle", "").strip(),
#                 "hint": data.get("hint", "").strip(),
#                 "answer": data.get("answer", "").strip()
#             }
#         except:
#             pass

#     # Fallback parse if bad JSON
#     lines = [l.strip() for l in out.splitlines() if l.strip()]
#     r = lines[0] if len(lines) > 0 else ""
#     h = lines[1] if len(lines) > 1 else ""
#     a = lines[2] if len(lines) > 2 else ""
#     return {"riddle": r, "hint": h, "answer": a}



