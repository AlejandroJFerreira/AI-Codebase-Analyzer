import os
import json
import requests
import chromadb
from dotenv import load_dotenv

load_dotenv()

client = chromadb.PersistentClient(path=".chroma")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

# Lighter settings for local inference
N_RESULTS = 5
MAX_CONTEXT_CHARS = 7000
REPO_MAP_PATH = ".repo_map.json"


def get_collection():
    return client.get_or_create_collection("codebase")


def load_repo_map():
    if not os.path.exists(REPO_MAP_PATH):
        return None
    with open(REPO_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_context_and_sources(question: str):
    collection = get_collection()

    results = collection.query(
        query_texts=[question],
        n_results=N_RESULTS,
        include=["documents", "metadatas"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        return None, []

    context_parts = []
    used = 0
    sources = []

    for doc, meta in zip(docs, metas):
        if used >= MAX_CONTEXT_CHARS:
            break

        label = f"FILE: {meta.get('path')} (chunk {meta.get('chunk')})\n"
        chunk_text = label + doc
        take = chunk_text[: max(0, MAX_CONTEXT_CHARS - used)]

        if take:
            context_parts.append(take)
            used += len(take)
            sources.append({
                "path": meta.get("path"),
                "chunk": meta.get("chunk")
            })

    context = "\n\n---\n\n".join(context_parts)
    return context, sources


def _call_ollama(prompt: str, stream: bool = False):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
        "options": {
            "num_ctx": 4096
        }
    }

    return requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        stream=stream,
        timeout=600
    )


def _build_prompt(question: str, context: str):
    repo_map = load_repo_map()
    repo_map_text = json.dumps(repo_map, indent=2)[:2000] if repo_map else "No repo map available."
    repo_map_sources = [{"path": ".repo_map.json", "chunk": "summary"}] if repo_map else []

    prompt = f"""You are a software engineer.

You are answering questions about a codebase.

Use BOTH:
1. the repository map for broad structural understanding
2. the retrieved code context for exact implementation details

If the question is broad, first identify the main modules/files involved, then explain their roles.
If you cannot answer from the provided information, say what is missing.

Repository map:
{repo_map_text}

Retrieved code context:
{context}

Question:
{question}
"""
    return prompt, repo_map_sources


def ask_codebase(question: str) -> dict:
    context, sources = _build_context_and_sources(question)

    if not context:
        return {
            "answer": "No documents found in the DB. Did you run ingest.py or ingest a GitHub repo?",
            "sources": []
        }

    prompt, repo_map_sources = _build_prompt(question, context)

    r = _call_ollama(prompt, stream=False)
    r.raise_for_status()
    data = r.json()

    answer = data["message"]["content"]
    return {"answer": answer, "sources": repo_map_sources + sources}


def stream_codebase_answer(question: str):
    context, _sources = _build_context_and_sources(question)

    if not context:
        yield "No documents found in the DB. Did you run ingest.py or ingest a GitHub repo?"
        return

    prompt, _repo_map_sources = _build_prompt(question, context)

    with _call_ollama(prompt, stream=True) as r:
        r.raise_for_status()

        for line in r.iter_lines():
            if not line:
                continue

            data = json.loads(line)
            msg = data.get("message")
            if msg and "content" in msg:
                yield msg["content"]