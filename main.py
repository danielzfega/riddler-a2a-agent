# app/main.py
from fastapi import FastAPI, Request
from app.models.a2a import *
from app.services.riddles import generate_riddle
from pydantic import BaseModel
import json, re, asyncio, os
from dotenv import load_dotenv


load_dotenv()


app = FastAPI(title="Riddler Agent", version="1.0.0")

# In-memory store: maps taskId -> {"riddle":..., "hint":..., "answer":..., "state": "asked"|"hint_shown"|"answered"}
_RIDDLE_STORE = {}
_STORE_LOCK = asyncio.Lock()


def clean_text(t: str) -> str:
    t = re.sub(r"<[^>]*>", "", t)
    return t.replace("\n", " ").strip()


def extract_text_from_parts(parts):
    candidates = []
    for p in parts:
        if p.get("kind") == "text" and p.get("text"):
            txt = clean_text(p["text"])
            if not txt:
                continue
            # ignore typical UI echoes
            if txt.lower().startswith(("fetching", "checking", "here are", "loading")):
                continue
            candidates.append(txt)
        if p.get("kind") == "data" and isinstance(p.get("data"), list):
            for inner in p["data"]:
                if inner.get("kind") == "text" and inner.get("text"):
                    txt = clean_text(inner["text"])
                    if not txt:
                        continue
                    if txt.lower().startswith(("fetching", "checking", "here are", "loading")):
                        continue
                    candidates.append(txt)

    if not candidates:
        return None
    # return last user text
    return candidates[-1]


def safe_parse_rpc(body):
    try:
        return JSONRPCRequest(**body)
    except Exception:
        class DummyRPC(BaseModel):
            id: str
            method: str
            params: dict
        return DummyRPC(**body)


def extract_prompt(rpc, body):
    msg_parts = (
        body.get("params", {}).get("message", {}).get("parts")
        or body.get("params", {}).get("messages", [{}])[-1].get("parts")
        or []
    )
    text = extract_text_from_parts(msg_parts)
    task_id = (
        body.get("params", {}).get("message", {}).get("taskId")
        or body.get("params", {}).get("taskId")
        or getattr(rpc, "id", None)
    )
    return text, task_id


@app.post("/a2a/riddler")
async def handle_a2a(req: Request):
    body = await req.json()
    print("\n📩 RAW REQUEST:\n", json.dumps(body, indent=2))

    rpc = safe_parse_rpc(body)
    user_text, task_id = extract_prompt(rpc, body)
    print("🧠 User Text:", user_text, " task:", task_id)

    if not user_text:
        # ask clarifying / default to new riddle
        user_text = "give me a riddle"

    # normalize
    lower = user_text.strip().lower()

    # Recognize commands: H for hint, A for answer, NEW for another riddle
    want_hint = lower in ("h", "hint", "give hint", "i want a hint")
    want_answer = lower in ("a", "answer", "give answer", "i want the answer")
    want_new = any(tok in lower for tok in ("new", "another", "another riddle", "give me another"))

    response_text = ""
    state = "completed"
    raw_artifact = ""

    try:
        async with _STORE_LOCK:
            record = _RIDDLE_STORE.get(task_id)

        # If user asks for hint/answer/new but we don't have a record, generate one
        if (want_hint or want_answer or want_new) and not record:
            # generate fresh riddle to pair with this session
            record = await generate_riddle(None)
            async with _STORE_LOCK:
                _RIDDLE_STORE[task_id] = {"riddle": record["riddle"], "hint": record["hint"], "answer": record["answer"], "state": "asked"}
            record = _RIDDLE_STORE[task_id]

        if want_new:
            # create a new riddle regardless
            rec = await generate_riddle(None)
            async with _STORE_LOCK:
                _RIDDLE_STORE[task_id] = {"riddle": rec["riddle"], "hint": rec["hint"], "answer": rec["answer"], "state": "asked"}
                record = _RIDDLE_STORE[task_id]
            response_text = (
                f"🧩 **Riddle**\n\n{record['riddle']}\n\n"
                "Reply with **H** for a hint, **A** for the answer, or **NEW** for another riddle."
            )

        elif want_hint:
            # show hint
            response_text = (
                f"💡 **Hint**\n\n{record['hint']}\n\n"
                "Reply with **A** for the answer or **NEW** for another riddle."
            )
            async with _STORE_LOCK:
                _RIDDLE_STORE[task_id]["state"] = "hint_shown"

        elif want_answer:
            response_text = (
                f"✅ **Answer**\n\n{record['answer']}\n\n"
                "Want another? Reply **NEW**."
            )
            async with _STORE_LOCK:
                _RIDDLE_STORE[task_id]["state"] = "answered"

        else:
            # treat as a "give me a riddle" prompt possibly with a topic
            # try to detect a topic: "give me a riddle about cats" -> topic "cats"
            topic = None
            m = re.search(r"riddle(?: about| on| for)? (.+)$", user_text, flags=re.IGNORECASE)
            if m:
                topic = m.group(1).strip()
            rec = await generate_riddle(topic)
            async with _STORE_LOCK:
                _RIDDLE_STORE[task_id] = {"riddle": rec["riddle"], "hint": rec["hint"], "answer": rec["answer"], "state": "asked"}
                record = _RIDDLE_STORE[task_id]

            response_text = (
                f"🧩 **Riddle**\n\n{record['riddle']}\n\n"
                "Reply with **H** for a hint, **A** for the answer, or **NEW** for another riddle."
            )

        raw_artifact = f"{record['riddle']} | hint: {record['hint']} | answer: {record['answer']}"

    except Exception as e:
        print("❌ Riddle error:", repr(e))
        response_text = f"⚠️ Riddle Agent Error: {str(e)}"
        raw_artifact = ""
        state = "failed"

    # Build A2A response
    agent_msg = A2AMessage(
        role="agent",
        parts=[MessagePart(kind="text", text=response_text)],
        taskId=task_id
    )

    result = TaskResult(
        id=task_id,
        contextId="riddler-riddle-context",
        status=TaskStatus(state=state, message=agent_msg),
        artifacts=[Artifact(name="riddle_raw", parts=[MessagePart(kind="text", text=raw_artifact)])],
        history=[agent_msg]
    )

    return JSONRPCResponse(id=rpc.id, result=result).model_dump()


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Riddler", "version": "1.0.0"}
