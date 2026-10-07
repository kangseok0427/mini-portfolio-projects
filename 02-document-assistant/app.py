from pathlib import Path
from uuid import UUID
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from rag.store import Store
from rag.search import search
from rag.providers import provider

ROOT = Path(__file__).parent.resolve()
load_dotenv(ROOT / ".env")
store = Store(ROOT / "data/documents.sqlite3")
app = FastAPI(title="AI 문서 분석 도우미")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
gate = asyncio.Semaphore(2)


class Question(BaseModel):
    session: str
    question: str = Field(min_length=1, max_length=2000)


def validate_session(value):
    try:
        UUID(value)
    except ValueError:
        raise HTTPException(400, "대화 식별자가 잘못되었습니다")


@app.get("/")
def index():
    return FileResponse(ROOT / "static/index.html")


@app.get("/api/documents")
def list_documents():
    return {"documents": store.documents(), "provider": provider().name}


@app.post("/api/documents")
async def upload(files: list[UploadFile] = File(...)):
    if len(files) > 10:
        raise HTTPException(400, "한 번에 10개 이하만 업로드해주세요")
    results = []
    for file in files:
        content = await file.read(10_000_001)
        name = Path((file.filename or "document").replace("\\", "/")).name[:180]
        try:
            results.append(
                dict(name=name, **await asyncio.to_thread(store.add, name, content))
            )
        except Exception as error:
            results.append({"name": name, "error": str(error)})
    return {"results": results}


@app.post("/api/demo")
def add_demo():
    results = [
        store.add(p.name, p.read_bytes())
        for p in sorted((ROOT / "demo/documents").glob("*"))
        if p.suffix in {".txt", ".pdf"}
    ]
    return {"results": results}


@app.delete("/api/documents/{identifier}")
def delete_document(identifier: str):
    store.remove(identifier)
    return {"ok": True}


@app.delete("/api/documents")
def reset():
    store.remove()
    return {"ok": True}


@app.get("/api/history/{session}")
def history(session: str):
    validate_session(session)
    return store.history(session)


@app.delete("/api/history/{session}")
def clear(session: str):
    validate_session(session)
    store.clear_history(session)
    return {"ok": True}


@app.post("/api/ask")
async def ask(data: Question):
    validate_session(data.session)
    question = data.question.strip()
    if not question:
        raise HTTPException(400, "질문을 입력해주세요")
    async with gate:
        history = await asyncio.to_thread(store.history, data.session)
        query = question
        if len(question) < 20 and history:
            query += " " + next(
                (m["text"] for m in reversed(history) if m["role"] == "user"), ""
            )
        sources = await asyncio.to_thread(search, store.corpus(), query)
        try:
            model = provider()
            answer = await model.answer(question, sources, history)
        except (ValueError, httpx.HTTPError) as error:
            message = (
                str(error)
                if isinstance(error, ValueError)
                else "LLM 네트워크 오류 또는 시간 초과"
            )
            raise HTTPException(502, message)
        await asyncio.to_thread(
            store.save_exchange, data.session, question, answer, sources
        )
        return {"answer": answer, "sources": sources, "provider": model.name}


import httpx
