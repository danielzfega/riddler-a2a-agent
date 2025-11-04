


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
    msg = body.get("params", {}).get("message", {})
    parts = msg.get("parts", [])

    # Extract latest human text, ignoring riddle-like text & history spam
    for p in reversed(parts):
        if p.get("kind") == "text":
            txt = p.get("text", "").strip()

            # ignore system / html / bot history artifacts
            if not txt or txt.startswith("<"):
                continue
            
            # Ignore text that looks like already generated riddles
            if any(w in txt.lower() for w in ["here's a riddle", "hint:", "answer:", "i have", "i can"]):
                continue
            
            # If text is extremely long, it's probably history, skip
            if len(txt) > 120:
                continue

            return txt

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
            f"💡 Hint: {record['hint']}\n\nReply A to see the answer or ask for another riddle."
        )


    if want_answer and record:
        return format_reply(task_id, record,
            f"✅ Answer: {record['answer']}\n\nAsk for another riddle anytime!"
        )


    # otherwise get new riddle
    rec = await generate_riddle()
    async with _STORE_LOCK:
        _RIDDLE_STORE[task_id] = rec


    text = f"🧩 Riddle:\n{rec['riddle']}"

    # Only show instruction if not a continuation
    text += "\n\nReply H for hint or A for answer."

    return format_reply(task_id, rec, text)



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
