import os
import requests
import chromadb
from dotenv import load_dotenv

load_dotenv()

# Must match ingest.py
client = chromadb.PersistentClient(path=".chroma")
collection = client.get_or_create_collection("codebase")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

N_RESULTS = 6
MAX_CONTEXT_CHARS = 12000  # BIG speed win

def ask_codebase(question: str) -> dict:
    results = collection.query(
        query_texts=[question],
        n_results=N_RESULTS,
        include=["documents", "metadatas"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        return {
            "answer": "No documents found in the DB. Did you run ingest.py?",
            "sources": []
        }

    # Build context gradually until we hit cap
    context_parts = []
    used = 0
    sources = []

    for doc, meta in zip(docs, metas):
        if used >= MAX_CONTEXT_CHARS:
            break
        take = doc[: max(0, MAX_CONTEXT_CHARS - used)]
        if take:
            context_parts.append(take)
            used += len(take)
            sources.append({"path": meta.get("path"), "chunk": meta.get("chunk")})

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a software engineer.

Answer the question about this codebase using ONLY the code context below.
If you can't answer from the context, say what file(s) you'd need.

Code context:
{context}

Question:
{question}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "num_ctx": 4096  # helps speed / memory on many machines
        }
    }

    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    answer = data["message"]["content"]
    return {"answer": answer, "sources": sources}