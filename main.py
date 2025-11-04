


from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.riddles import generate_riddle
from pydantic import BaseModel
import json, re, asyncio
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Riddler Agent", version="1.2.0")

# Store riddle context per session (taskId)
_RIDDLE_STORE = {}
_STORE_LOCK = asyncio.Lock()


def extract_user_text(body):
    parts = (
        body.get("params", {}).get("message", {}).get("parts")
        or body.get("params", {}).get("messages", [{}])[-1].get("parts")
        or []
    )
    for p in parts:
        if p.get("kind") == "text":
            return p.get("text", "").strip()
    return None


def extract_task_id(body):
    return (
        body.get("params", {}).get("message", {}).get("taskId")
        or body.get("params", {}).get("taskId")
        or None
    )


@app.post("/a2a/riddler")
async def riddler(req: Request):
    body = await req.json()
    user_text = extract_user_text(body) or ""
    task_id = extract_task_id(body)

    lower = user_text.lower().strip()
    want_hint = lower == "h"
    want_answer = lower == "a"

    async with _STORE_LOCK:
        record = _RIDDLE_STORE.get(task_id)

    # ↪️ If user pressed H/A but no riddle exists — create one first
    if (want_hint or want_answer) and not record:
        record = await generate_riddle()
        async with _STORE_LOCK:
            _RIDDLE_STORE[task_id] = record

    # 🎯 User wants hint
    if want_hint and record:
        return format_reply(
            task_id,
            record,
            f"💡 Hint: {record['hint']}\n\nPress **A** for the answer."
        )

    # 🎯 User wants answer
    if want_answer and record:
        return format_reply(
            task_id,
            record,
            f"✅ Answer: {record['answer']}\n\nAsk anything for a new riddle."
        )

    # ➕ Any other text = generate NEW riddle
    rec = await generate_riddle()
    async with _STORE_LOCK:
        _RIDDLE_STORE[task_id] = rec

    return format_reply(
        task_id,
        rec,
        f"🧩 Riddle:\n{rec['riddle']}\n\nPress **H** for hint or **A** for answer."
    )


def format_reply(task_id, rec, text):
    agent_msg = A2AMessage(
        role="agent",
        taskId=task_id,
        parts=[MessagePart(kind="text", text=text)]
    )

    result = TaskResult(
        id=task_id,
        contextId="riddle-session",
        status=TaskStatus(state="completed", message=agent_msg),
        artifacts=[
            Artifact(
                name="riddle_data",
                parts=[MessagePart(
                    kind="text",
                    text=f"{rec['riddle']} | hint: {rec['hint']} | answer: {rec['answer']}"
                )]
            )
        ],
        history=[agent_msg]
    )

    return JSONRPCResponse(id=task_id, result=result).model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Riddler", "version": "1.0.1"}
