from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.riddles import generate_riddle
import asyncio

app = FastAPI(title="Riddler Agent", version="3.0.0")

_RIDDLE_STORE = {}
_LOCK = asyncio.Lock()


def extract_user_text(body):
    parts = body.get("params", {}).get("message", {}).get("parts", [])
    for p in reversed(parts):
        if p.get("kind") != "text":
            continue
        t = p.get("text", "").strip()
        if not t or t.startswith("<") or len(t) > 160:
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

    async with _LOCK:
        record = _RIDDLE_STORE.get(task_id)

    # Handle riddle requests
    if "riddle" in user_text or "give me" in user_text:
        new_riddle = await generate_riddle(user_text)
        async with _LOCK:
            _RIDDLE_STORE[task_id] = new_riddle

        return reply(
            task_id,
            new_riddle,
            f"🧩 Riddle:\n{new_riddle['riddle']}\n\n💡 Hint: {new_riddle['hint']}\n✅ Answer: {new_riddle['answer']}\n\nSay 'give me another riddle' for more!"
        )

    # Default fallback message
    return reply(
        task_id,
        record or {"riddle": "", "hint": "", "answer": ""},
        "Say 'give me a riddle' or 'give me a riddle about space, Egypt, love, or technology.'"
    )


def reply(task_id, rec, text):
    artifact_text = f"riddle: {rec.get('riddle','')}\nhint: {rec.get('hint','')}\nanswer: {rec.get('answer','')}"

    agent_msg = A2AMessage(
        role="agent",
        taskId=task_id,
        parts=[MessagePart(kind="text", text=text)],
    )

    result = TaskResult(
        id=task_id,
        contextId="riddle-session",
        status=TaskStatus(state="completed", message=agent_msg),
        artifacts=[
            Artifact(
                name="riddle_data",
                parts=[MessagePart(kind="text", text=artifact_text)],
            )
        ],
        history=[agent_msg],
    )

    return JSONRPCResponse(id=task_id, result=result).model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Riddler 3.0.0"}
