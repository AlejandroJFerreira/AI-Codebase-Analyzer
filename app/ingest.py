import os
import hashlib
import shutil
import tempfile
import subprocess
from urllib.parse import urlparse

import chromadb

client = chromadb.PersistentClient(path=".chroma")
collection = client.get_or_create_collection("codebase")

SKIP_DIRS = {
    ".venv", ".git", "__pycache__", ".chroma", ".pytest_cache", "node_modules",
    "dist", "build", "out", ".next", "target", ".idea", ".vscode"
}
EXTS = (".py", ".js", ".ts", ".cpp", ".c", ".h", ".hpp", ".java", ".cs", ".md")

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
MAX_FILE_CHARS = 300_000


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []

    chunks = []
    step = max(1, size - overlap)

    for start in range(0, len(text), step):
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break

    return chunks


def stable_id(path: str, chunk_index: int) -> str:
    key = f"{path}:{chunk_index}".encode("utf-8", errors="ignore")
    return hashlib.sha1(key).hexdigest()


def clear_collection() -> None:
    global collection
    try:
        client.delete_collection("codebase")
    except Exception:
        pass
    collection = client.get_or_create_collection("codebase")


def ingest_project(folder: str) -> dict:
    total_chunks = 0
    total_files = 0
    batch_size = 64

    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict] = []

    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if not file.endswith(EXTS):
                continue

            path = os.path.join(root, file)

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                print(f"Skipping {path}: {e}")
                continue

            if len(content) > MAX_FILE_CHARS:
                print(f"Skipping huge file: {path} ({len(content)} chars)")
                continue

            chunks = chunk_text(content)
            total_files += 1

            for i, chunk in enumerate(chunks):
                docs.append(chunk)
                ids.append(stable_id(path, i))
                metas.append({"path": path, "chunk": i})

                total_chunks += 1

                if len(docs) >= batch_size:
                    collection.add(documents=docs, ids=ids, metadatas=metas)
                    print(f"Added batch. Total chunks indexed: {total_chunks}")
                    docs, ids, metas = [], [], []

            print(f"Queued: {path} ({len(chunks)} chunks)")

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)

    print(f"Done. Indexed {total_files} files / {total_chunks} chunks into ChromaDB.")
    return {"files_indexed": total_files, "chunks_indexed": total_chunks}


def clone_repo(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https GitHub URLs are supported.")

    temp_dir = tempfile.mkdtemp(prefix="repo_ingest_")
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, temp_dir],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return temp_dir


def ingest_github_repo(repo_url: str) -> dict:
    temp_dir = None
    try:
        clear_collection()
        temp_dir = clone_repo(repo_url)
        stats = ingest_project(temp_dir)
        return {
            "repo_url": repo_url,
            "files_indexed": stats["files_indexed"],
            "chunks_indexed": stats["chunks_indexed"]
        }
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    folder = input("Enter path to codebase folder: ").strip().strip('"')
    clear_collection()
    ingest_project(folder)