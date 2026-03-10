from pathlib import Path
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.query import ask_codebase, stream_codebase_answer
from app.ingest import ingest_github_repo

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
REPO_MAP_PATH = BASE_DIR / ".repo_map.json"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class RepoRequest(BaseModel):
    repo_url: str


@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/ask")
def ask(question: str):
    return ask_codebase(question)


@app.get("/ask_stream")
def ask_stream(question: str):
    return StreamingResponse(
        stream_codebase_answer(question),
        media_type="text/plain"
    )


@app.post("/ingest_github")
def ingest_repo(request: RepoRequest):
    try:
        return ingest_github_repo(request.repo_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/repo_map")
def repo_map():
    if not REPO_MAP_PATH.exists():
        return {"message": "No repo map available yet."}

    with open(REPO_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)