from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.riddles import generate_riddle
import asyncio
import re

app = FastAPI(title="Riddler Agent", version="2.1.0")

_RIDDLE_STORE = {}
_LOCK = asyncio.Lock()

def extract_user_text(body):
    parts = body.get("params", {}).get("message", {}).get("parts", [])

    for p in reversed(parts):
        if p.get("kind") != "text":
            continue

        t = p.get("text", "").strip()

        if not t or t.startswith("<"):
            continue
        if len(t) > 160:
            continue

        return t

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
    user_text = extract_user_text(body).lower()
    task_id = extract_task_id(body)

    want_hint = user_text == "h"
    want_answer = user_text == "a"

    async with _LOCK:
        record = _RIDDLE_STORE.get(task_id)

    if (want_hint or want_answer) and not record:
        record = await generate_riddle()
        async with _LOCK:
            _RIDDLE_STORE[task_id] = record

    if want_hint and record:
        return reply(task_id, record, f"💡 Hint: {record['hint']}\n\nReply A for answer.")

    if want_answer and record:
        return reply(task_id, record, f"✅ Answer: {record['answer']}\n\nSay 'give me a riddle' for another!")

    new_riddle = await generate_riddle(user_text)
    async with _LOCK:
        _RIDDLE_STORE[task_id] = new_riddle

    return reply(task_id, new_riddle, f"🧩 Riddle:\n{new_riddle['riddle']}\n\nReply H for hint or A for answer.")

def reply(task_id, rec, text):
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
                parts=[MessagePart(kind="text", text=f"riddle: {rec['riddle']}\nhint: {rec['hint']}\nanswer: {rec['answer']}")]
            )
        ],
        history=[agent_msg],
    )

    return JSONRPCResponse(id=task_id, result=result).model_dump()

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Riddler 2.1.0"}
