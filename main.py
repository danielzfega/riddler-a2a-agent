


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
    # Telex sometimes sends previous history + data noise.
    # We only take the LAST text message the user sent.

    msg = body.get("params", {}).get("message", {})
    parts = msg.get("parts", [])

    # Reverse to get latest meaningful text
    for p in reversed(parts):
        if p.get("kind") == "text":
            txt = p.get("text", "").strip()
            # ignore HTML and system artifacts
            if txt and not txt.startswith("<"):
                return txt

    # fallback: maybe in params.messages
    messages = body.get("params", {}).get("messages", [])
    if messages:
        for p in reversed(messages[-1].get("parts", [])):
            if p.get("kind") == "text":
                return p.get("text", "").strip()

    return ""


def extract_task_id(body):
    tid = (
        body.get("params", {}).get("message", {}).get("taskId")
        or body.get("params", {}).get("taskId")
    )
    # fallback if Telex didn't send one
    return tid or f"task-{int(asyncio.get_event_loop().time()*1000)}"



@app.post("/a2a/riddler")
async def riddler(req: Request):
    body = await req.json()
    user_text = extract_user_text(body)
    task_id = extract_task_id(body)

    lower = user_text.lower().strip()
    want_hint = lower == "h"
    want_answer = lower == "a"

    async with _STORE_LOCK:
        record = _RIDDLE_STORE.get(task_id)

    if (want_hint or want_answer) and not record:
        record = await generate_riddle()
        async with _STORE_LOCK:
            _RIDDLE_STORE[task_id] = record

    if want_hint and record:
        return format_reply(task_id, record,
            f"💡 Hint: {record['hint']}\n\nReply A to see the answer."
        )

    if want_answer and record:
        return format_reply(task_id, record,
            f"✅ Answer: {record['answer']}\n\nReply anything to get a new riddle!"
        )

    # otherwise get new riddle
    rec = await generate_riddle()
    async with _STORE_LOCK:
        _RIDDLE_STORE[task_id] = rec

    return format_reply(task_id, rec,
        f"🧩 Riddle:\n{rec['riddle']}\n\nReply H for hint or A for answer."
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
