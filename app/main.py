from fastapi import FastAPI
from app.query import ask_codebase

app = FastAPI()

@app.get("/")
def root():
    return {"message": "AI Codebase Analyzer Running"}

@app.get("/ask")
def ask(question: str):
    return ask_codebase(question)