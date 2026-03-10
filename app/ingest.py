import os
import json
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
EXTS = (".py", ".js", ".ts", ".cpp", ".c", ".h", ".hpp", ".java", ".cs", ".md", ".html", ".css")

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
MAX_FILE_CHARS = 300_000

REPO_MAP_PATH = ".repo_map.json"


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


def classify_file(path: str) -> str:
    p = path.replace("\\", "/").lower()
    name = os.path.basename(p)

    if name in {"package.json", "package-lock.json", "requirements.txt", "pom.xml"}:
        return "config"
    if "/test" in p or "/tests" in p or name.startswith("test_"):
        return "tests"
    if name.endswith((".md", ".txt")):
        return "docs"
    if name.endswith((".html", ".css")):
        return "frontend"
    if name.endswith((".js", ".ts")):
        if "handler" in name or "event" in name or "mouse" in name or "keyboard" in name or "timer" in name:
            return "handlers"
        if "client" in name or "button" in name or "canvas" in name:
            return "frontend"
        return "javascript"
    if name.endswith((".py", ".java", ".cs", ".cpp", ".c", ".h", ".hpp")):
        return "backend_or_systems"
    return "other"


def save_repo_map(repo_name: str, repo_source: str, indexed_files: list[dict], total_chunks: int) -> None:
    groups: dict[str, list[str]] = {}

    for file_info in indexed_files:
        category = file_info["category"]
        groups.setdefault(category, []).append(file_info["relative_path"])

    repo_map = {
        "repo_name": repo_name,
        "repo_source": repo_source,
        "files_indexed": len(indexed_files),
        "chunks_indexed": total_chunks,
        "files": indexed_files,
        "groups": groups,
    }

    with open(REPO_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(repo_map, f, indent=2)


def ingest_project(folder: str, repo_name: str | None = None, repo_source: str | None = None) -> dict:
    total_chunks = 0
    total_files = 0
    batch_size = 64

    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict] = []
    indexed_files: list[dict] = []

    if repo_name is None:
        repo_name = os.path.basename(folder.rstrip("\\/")) or "local_repo"
    if repo_source is None:
        repo_source = folder

    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if not file.endswith(EXTS):
                continue

            path = os.path.join(root, file)
            relative_path = os.path.relpath(path, folder)

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
            category = classify_file(relative_path)

            indexed_files.append({
                "relative_path": relative_path.replace("\\", "/"),
                "category": category,
                "chars": len(content),
                "chunks": len(chunks),
            })

            total_files += 1

            for i, chunk in enumerate(chunks):
                docs.append(chunk)
                ids.append(stable_id(relative_path, i))
                metas.append({
                    "path": relative_path.replace("\\", "/"),
                    "chunk": i,
                    "category": category,
                })

                total_chunks += 1

                if len(docs) >= batch_size:
                    collection.add(documents=docs, ids=ids, metadatas=metas)
                    print(f"Added batch. Total chunks indexed: {total_chunks}")
                    docs, ids, metas = [], [], []

            print(f"Queued: {relative_path} ({len(chunks)} chunks)")

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)

    save_repo_map(repo_name, repo_source, indexed_files, total_chunks)

    print(f"Done. Indexed {total_files} files / {total_chunks} chunks into ChromaDB.")
    return {
        "files_indexed": total_files,
        "chunks_indexed": total_chunks,
        "repo_name": repo_name,
        "repo_source": repo_source,
    }


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


def infer_repo_name_from_url(repo_url: str) -> str:
    tail = repo_url.rstrip("/").split("/")[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail or "github_repo"


def ingest_github_repo(repo_url: str) -> dict:
    temp_dir = None
    try:
        clear_collection()
        temp_dir = clone_repo(repo_url)
        repo_name = infer_repo_name_from_url(repo_url)
        stats = ingest_project(temp_dir, repo_name=repo_name, repo_source=repo_url)
        return {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "files_indexed": stats["files_indexed"],
            "chunks_indexed": stats["chunks_indexed"],
        }
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    folder = input("Enter path to codebase folder: ").strip().strip('"')
    clear_collection()
    ingest_project(folder)