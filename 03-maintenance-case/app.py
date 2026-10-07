import os, time
from pathlib import Path
from uuid import uuid4
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from before.legacy import sync as legacy, LegacyFailure
from after.sync import sync as repaired
from after.export import export
from dataset import PAGES

ROOT = Path(__file__).parent.resolve()
load_dotenv(ROOT / ".env")
app = FastAPI(title="주문 동기화 유지보수 사례")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
jobs = {}
attempts = {}
lock = Lock()
pool = ThreadPoolExecutor(max_workers=2)


@app.get("/")
def index():
    return FileResponse(ROOT / "static/index.html")


@app.get("/api/mock/orders")
def mock(page: int = 1, run: str = "demo"):
    if page == 2:
        with lock:
            key = (run, page)
            count = attempts.get(key, 0)
            attempts[key] = count + 1
            if len(attempts) > 200:
                attempts.pop(next(iter(attempts)))
        if count == 0:
            raise HTTPException(503, "주문 서비스 일시 장애 — 데모 오류 주입")
    return PAGES.get(page, [])


@app.post("/api/run/{version}")
def start(version: str):
    if version not in {"before", "after"}:
        raise HTTPException(400, "버전 오류")
    identifier = uuid4().hex
    with lock:
        if sum(j["status"] == "running" for j in jobs.values()) >= 2:
            raise HTTPException(429, "잠시 후 다시 실행해주세요")
        if len(jobs) >= 100:
            raise HTTPException(
                429, "데모 작업 한도에 도달했습니다. 서버를 재시작해주세요"
            )
        jobs[identifier] = {
            "status": "running",
            "version": version,
            "logs": [],
            "rows": [],
            "files": [],
        }
    pool.submit(run, identifier, version)
    return {"id": identifier}


def run(identifier, version):
    folder = ROOT / "output" / identifier
    folder.mkdir(parents=True, exist_ok=True)
    began = time.perf_counter()

    def log(text):
        with lock:
            jobs[identifier]["logs"].append(text)

    def fetch(page):
        # BEFORE retains its old hardcoded endpoint; AFTER reads configuration.
        url = (
            "http://127.0.0.1:8103/api/mock/orders"
            if version == "before"
            else os.getenv("API_BASE_URL", "http://127.0.0.1:8103/api/mock/orders")
        )
        with httpx.Client(
            timeout=float(os.getenv("API_TIMEOUT", "5")), trust_env=False
        ) as client:
            response = client.get(url, params={"page": page, "run": identifier})
            response.raise_for_status()
            return response.json()

    try:
        if version == "before":
            rows = legacy(fetch, folder, log)
            duplicates = len(rows) - len({r["id"] for r in rows})
            errors = []
            retries = 0
        else:
            rows, duplicates, errors, retries = repaired(
                fetch, folder, log, retries=int(os.getenv("API_RETRIES", "2"))
            )
            export(rows, folder)
        log("작업 완료")
        status = "done"
    except LegacyFailure as error:
        rows = error.rows
        duplicates = len(rows) - len({r["id"] for r in rows})
        errors = [str(error)]
        retries = 0
        status = "failed"
        log("예외 발생 → 전체 작업 종료")
    except Exception as error:
        rows = []
        duplicates = 0
        errors = [str(error)]
        retries = 0
        status = "failed"
        log("실행 오류")
    with lock:
        jobs[identifier].update(
            status=status,
            rows=rows,
            duplicates=duplicates,
            errors=errors,
            retries=retries,
            elapsed_ms=round((time.perf_counter() - began) * 1000),
            files=[
                p.name
                for p in folder.iterdir()
                if p.suffix in {".csv", ".xlsx", ".sqlite3"}
            ],
        )


@app.get("/api/jobs/{identifier}")
def status(identifier: str):
    with lock:
        if identifier not in jobs:
            raise HTTPException(404, "작업 없음")
        return dict(jobs[identifier])


@app.get("/api/jobs/{identifier}/files/{name}")
def download(identifier: str, name: str):
    with lock:
        if identifier not in jobs or name not in jobs[identifier]["files"]:
            raise HTTPException(404, "파일 없음")
    return FileResponse(ROOT / "output" / identifier / name, filename=name)
