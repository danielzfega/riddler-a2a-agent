from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.riddles import generate_riddle
import asyncio

app = FastAPI(title="Riddler Agent", version="2.0.0")

_RIDDLE_STORE = {}
_STORE_LOCK = asyncio.Lock()


def extract_user_text(body):
    msg = body.get("params", {}).get("message", {})
    parts = msg.get("parts", [])
    
    for p in reversed(parts):
        if p.get("kind") == "text":
            txt = p.get("text", "").strip()

            if not txt or txt.startswith("<"):
                continue
            if len(txt) > 120:
                continue
            if txt.lower() in ["h", "a"]:
                continue

            return txt

    return ""


def extract_task_id(body):
    tid = (
        body.get("params", {}).get("message", {}).get("taskId")
        or body.get("params", {}).get("taskId")
    )
    return tid or f"task-{int(asyncio.get_event_loop().time()*1000)}"


@app.post("/a2a/riddler")
async def riddler(req: Request):
    body = await req.json()
    user_text = extract_user_text(body)
    task_id = extract_task_id(body)

    lower = user_text.lower()
    want_hint = lower == "h"
    want_answer = lower == "a"

    async with _STORE_LOCK:
        record = _RIDDLE_STORE.get(task_id)

    if (want_hint or want_answer) and not record:
        record = await generate_riddle()
        async with _STORE_LOCK:
            _RIDDLE_STORE[task_id] = record

    if want_hint and record:
        return reply(task_id, record, f"💡 Hint: {record['hint']}\n\nReply A for answer.")

    if want_answer and record:
        return reply(task_id, record, f"✅ Answer: {record['answer']}\n\nAsk for another riddle anytime!")

    # otherwise generate new riddle + store
    new_record = await generate_riddle(user_text)
    async with _STORE_LOCK:
        _RIDDLE_STORE[task_id] = new_record

    text = f"🧩 Riddle:\n{new_record['riddle']}\n\nReply H for hint or A for answer."
    return reply(task_id, new_record, text)


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
                parts=[MessagePart(
                    kind="text",
                    text=f"riddle: {rec['riddle']}\nhint: {rec['hint']}\nanswer: {rec['answer']}"
                )]
            )
        ],
        history=[agent_msg],
    )

    return JSONRPCResponse(id=task_id, result=result).model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Riddler", "version": "2.0.0"}




