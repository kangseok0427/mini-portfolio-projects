from pathlib import Path
from uuid import uuid4
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from collector.pipeline import collect

ROOT = Path(__file__).parent.resolve()
load_dotenv(ROOT / ".env")
app = FastAPI(title="상품정보 수집기")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
jobs = {}
lock = Lock()
executor = ThreadPoolExecutor(max_workers=2)


class Request(BaseModel):
    query: str = Field(default="", max_length=2000)
    source: str = "demo"
    max_pages: int = Field(default=3, ge=1, le=5)


@app.get("/")
def index():
    return FileResponse(ROOT / "static/index.html")


@app.post("/api/jobs")
def start(data: Request):
    if data.source not in {"demo", "web"}:
        raise HTTPException(400, "수집 출처 오류")
    job_id = uuid4().hex
    with lock:
        if sum(j["status"] == "running" for j in jobs.values()) >= 2:
            raise HTTPException(429, "진행 중인 작업이 있습니다")
        if len(jobs) >= 100:
            old = next((k for k, v in jobs.items() if v["status"] != "running"), None)
            if old:
                jobs.pop(old)
                (ROOT / "output" / f"{old}.xlsx").unlink(missing_ok=True)
        jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "message": "수집 준비 중",
            "products": [],
            "errors": [],
        }
    executor.submit(run, job_id, data)
    return {"id": job_id}


def run(job_id, data):
    def update(percent, message):
        with lock:
            jobs[job_id].update(progress=percent, message=message)

    try:
        products, duplicates, errors = collect(
            data.query,
            data.source,
            data.max_pages,
            ROOT / "output" / f"{job_id}.xlsx",
            update,
        )
        with lock:
            jobs[job_id].update(
                status="done",
                progress=100,
                message="Excel 생성 완료",
                products=[p.to_dict() for p in products],
                duplicates=duplicates,
                errors=errors,
                download=f"/api/jobs/{job_id}/excel",
                save_path=f"output/{job_id}.xlsx",
            )
    except Exception as error:
        with lock:
            jobs[job_id].update(status="failed", message=f"작업 실패: {error}")


@app.get("/api/jobs/{job_id}")
def status(job_id: str):
    with lock:
        if job_id not in jobs:
            raise HTTPException(404, "작업을 찾을 수 없습니다")
        return dict(jobs[job_id])


@app.get("/api/jobs/{job_id}/excel")
def download(job_id: str):
    with lock:
        if job_id not in jobs or jobs[job_id]["status"] != "done":
            raise HTTPException(404, "파일이 준비되지 않았습니다")
    return FileResponse(ROOT / "output" / f"{job_id}.xlsx", filename="products.xlsx")
