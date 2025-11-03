# app/services/riddles.py
import os
import httpx
import asyncio
from typing import Dict, Any

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = os.getenv("HF_MODEL", "sshleifer/distilbart-cnn-12-6")

# a very small concurrency lock for the riddle store if needed
_store_lock = asyncio.Lock()

async def call_gemini(prompt: str, max_tokens: int = 200) -> str:
    """
    Call Gemini-style LLM endpoint. This is intentionally generic:
    - Expects a Bearer token in GEMINI_API_KEY.
    - Expects GEMINI_API_URL to accept JSON { "prompt": "...", "max_output_tokens": N }
    - Adjust according to the real Gemini API you have access to.
    """
    if not GEMINI_API_KEY or not GEMINI_API_URL:
        raise RuntimeError("Gemini config not set")

    payload = {
        "prompt": prompt,
        "max_output_tokens": max_tokens,
        # you can expose temperature etc here if your endpoint supports it
        "temperature": 0.95
    }

    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(GEMINI_API_URL, json=payload, headers=headers)
        r.raise_for_status()
        js = r.json()

    # adapt to the shape your Gemini endpoint returns.
    # common patterns: {"output": "..." } or {"candidates":[{"output":"..."}]}
    if isinstance(js, dict):
        if "output" in js and isinstance(js["output"], str):
            return js["output"].strip()
        if "candidates" in js and isinstance(js["candidates"], list) and js["candidates"]:
            return js["candidates"][0].get("output", "").strip()
        # Vertex AI style: responses[0].content[0].text ?
        if "responses" in js:
            try:
                return js["responses"][0]["content"][0]["text"].strip()
            except Exception:
                pass

    # fallback to a string of the whole JSON
    return str(js)

async def call_hf(prompt: str, max_tokens: int = 200) -> str:
    """
    Hugging Face Inference fallback. Uses HF API to call a model set in HF_MODEL.
    """
    if not HF_API_KEY:
        raise RuntimeError("HF_API_KEY not set for fallback")
    model = HF_MODEL
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": 0.8}}
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"https://api-inference.huggingface.co/models/{model}"
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        js = r.json()

    # HF returns list of outputs for many models
    if isinstance(js, list) and js and isinstance(js[0], dict) and "generated_text" in js[0]:
        return js[0]["generated_text"].strip()
    if isinstance(js, dict) and "generated_text" in js:
        return js["generated_text"].strip()
    # some models return [{"summary_text": "..."}] for summarizers
    if isinstance(js, list) and js and "summary_text" in js[0]:
        return js[0]["summary_text"].strip()

    return str(js)

async def generate_riddle(topic: str = None) -> Dict[str, str]:
    """
    Use the LLM to generate a riddle, a short hint, and the answer.
    Returns {"riddle": ..., "hint": ..., "answer": ...}
    """
    topic_text = f" about {topic}" if topic else ""
    prompt = (
        f"Create a single original riddle{topic_text}. Output JSON only with keys: riddle, hint, answer.\n"
        "Make the riddle moderately challenging but fair. Hint should be one short sentence. Answer should be one short word/phrase.\n\n"
        "Example output:\n"
        '{"riddle": "I have keys but no locks...", "hint": "You'll find me where letters live.", "answer": "keyboard"}\n\nNow create a new one."
    )

    # Try Gemini first; on failure fallback to HF
    try:
        out = await call_gemini(prompt, max_tokens=200)
    except Exception as e:
        # try HF fallback
        out = None
        try:
            out = await call_hf(prompt, max_tokens=200)
        except Exception as e2:
            raise RuntimeError(f"Both Gemini and HF failed: {e} / {e2}")

    # Try to extract JSON from output (LLMs often return JSON or similar)
    import re, json
    # naive search for a JSON object in the output
    m = re.search(r"(\{[\s\S]*\})", out)
    if m:
        try:
            data = json.loads(m.group(1))
            r = data.get("riddle") or data.get("question") or data.get("q") or ""
            h = data.get("hint") or ""
            a = data.get("answer") or data.get("ans") or ""
            return {"riddle": r.strip(), "hint": h.strip(), "answer": a.strip()}
        except Exception:
            pass

    # fallback parsing heuristics: split by lines
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    r, h, a = "", "", ""
    # attempt: first non-empty -> riddle, next -> hint, next -> answer
    if lines:
        r = lines[0]
    if len(lines) >= 2:
        h = lines[1]
    if len(lines) >= 3:
        a = lines[2]

    return {"riddle": r, "hint": h, "answer": a}
