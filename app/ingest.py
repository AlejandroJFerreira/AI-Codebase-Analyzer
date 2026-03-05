import os
import hashlib
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
MAX_FILE_CHARS = 300_000  # skip gigantic files

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
    # Stable + short ID for Chroma
    key = f"{path}:{chunk_index}".encode("utf-8", errors="ignore")
    return hashlib.sha1(key).hexdigest()

def ingest_project(folder: str) -> None:
    total_chunks = 0
    BATCH = 64

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

            for i, chunk in enumerate(chunks):
                docs.append(chunk)
                ids.append(stable_id(path, i))
                metas.append({"path": path, "chunk": i})

                total_chunks += 1

                if len(docs) >= BATCH:
                    collection.add(documents=docs, ids=ids, metadatas=metas)
                    print(f"Added batch. Total chunks indexed: {total_chunks}")
                    docs, ids, metas = [], [], []

            print(f"Queued: {path} ({len(chunks)} chunks)")

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)

    print(f"Done. Indexed {total_chunks} chunks into ChromaDB.")

if __name__ == "__main__":
    folder = input("Enter path to codebase folder: ").strip().strip('"')
    ingest_project(folder)