from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from app.query import ask_codebase, stream_codebase_answer

app = FastAPI()

@app.get("/")
def root():
    return {"message": "AI Codebase Analyzer Running"}

# Normal JSON endpoint
@app.get("/ask")
def ask(question: str):
    return ask_codebase(question)

# Streaming endpoint
@app.get("/ask_stream")
def ask_stream(question: str):
    return StreamingResponse(
        stream_codebase_answer(question),
        media_type="text/plain"
    )