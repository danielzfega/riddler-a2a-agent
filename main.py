from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.riddles import generate_riddle
import asyncio

app = FastAPI(title="Riddler Agent", version="2.1.0")

_RIDDLE_STORE = {}
_LOCK = asyncio.Lock()


def extract_user_text(body):
    msg = body.get("params", {}).get("message", {})
    parts = msg.get("parts", [])

    for p in reversed(parts):
        if p.get("kind") == "text":
            txt = p.get("text", "").strip()
            if txt and not txt.startswith("<") and len(txt) <= 200:
                return txt
    return ""


def extract_task_id(body):
    return (
        body.get("params", {}).get("message", {}).get("taskId")
        or body.get("params", {}).get("taskId")
        or f"task-{int(asyncio.get_event_loop().time()*1000)}"
    )


@app.post("/a2a/riddler")
async def riddler(req: Request):
    body = await req.json()
    user_text = extract_user_text(body)
    task_id = extract_task_id(body)

    lower = user_text.lower().strip()
    want_hint = lower == "h"
    want_answer = lower == "a"

    async with _LOCK:
        record = _RIDDLE_STORE.get(task_id)

    # If user wants hint/answer but no riddle exists yet, create one
    if (want_hint or want_answer) and not record:
        record = await generate_riddle()
        async with _LOCK:
            _RIDDLE_STORE[task_id] = record

    if want_hint:
        return format_reply(task_id, record, f"💡 Hint: {record['hint']}\n\nReply A for answer.")

    if want_answer:
        return format_reply(task_id, record, f"✅ Answer: {record['answer']}\n\nSay 'riddle' for a new one.")

    # Otherwise create new riddle (with topic if user asked)
    new_rec = await generate_riddle(user_text)
    async with _LOCK:
        _RIDDLE_STORE[task_id] = new_rec

    return format_reply(
        task_id,
        new_rec,
        f"🧩 Riddle:\n{new_rec['riddle']}\n\nReply H for hint or A for answer."
    )


def format_reply(task_id, rec, text):
    msg = A2AMessage(
        role="agent",
        taskId=task_id,
        parts=[MessagePart(kind="text", text=text)]
    )

    return JSONRPCResponse(
        id=task_id,
        result=TaskResult(
            id=task_id,
            contextId="riddle-session",
            status=TaskStatus(state="completed", message=msg),
            artifacts=[
                Artifact(
                    name="riddle_data",
                    parts=[MessagePart(
                        kind="text",
                        text=f"riddle: {rec['riddle']}\nhint: {rec['hint']}\nanswer: {rec['answer']}"
                    )]
                )
            ],
            history=[msg]
        )
    ).model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Riddler", "version": "2.1.0"}
