from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.query import ask_codebase, stream_codebase_answer

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Optional: if you add CSS/JS files later, this will serve them
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


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