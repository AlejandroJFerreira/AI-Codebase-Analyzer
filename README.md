# AI Codebase Analyzer

AI Codebase Analyzer is a Retrieval-Augmented Generation (RAG) tool that ingests a local or GitHub-hosted repository, indexes its source code into a vector database, and answers natural language questions about the codebase using a local LLM.

The system combines repository structure metadata, semantic code retrieval, and LLM-based reasoning to help users understand unfamiliar repositories, identify important files, and inspect implementation details.

## Features

- Natural language Q&A over indexed codebases
- GitHub repository ingestion by URL
- Chunked code indexing for semantic retrieval
- Vector search using **ChromaDB**
- Local LLM inference through **Ollama**
- FastAPI backend for querying and ingestion
- Browser-based frontend interface
- Streaming responses for interactive Q&A
- Cited source files and chunk references in answers
- Repository map support for broader architecture questions
- Skips unnecessary directories such as virtual environments and build artifacts

## How It Works

1. A repository is ingested from either:
   - a local folder path, or
   - a public GitHub repository URL
2. Source files are split into overlapping chunks
3. Chunks are stored in **ChromaDB** with file metadata
4. A lightweight repository map is generated to capture file structure
5. A user asks a question through the API or frontend
6. Relevant chunks are retrieved from the vector database
7. The local LLM uses both:
   - retrieved code context
   - repository map information
8. The system returns an answer with cited sources

## Architecture

```
Codebase → Ingestion → Chunking → ChromaDB (vector store)
                                ↓
                        Semantic Retrieval
                                ↓
User Question → FastAPI → Repo Map + Context Assembly → Ollama LLM → Answer
```

## Project Structure

```text
ai-codebase-analyzer
│
├── app
│   ├── main.py
│   ├── ingest.py
│   ├── query.py
│   └── __init__.py
│
├── frontend
│   └── index.html
│
├── .chroma
├── .repo_map.json
├── .env
├── .gitignore
└── README.md
```

## Supported File Types

The ingestion pipeline currently indexes source and documentation files with these extensions:

```text
.py, .js, .ts, .cpp, .c, .h, .hpp, .java, .cs, .md, .html, .css
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/AlejandroJFerreira/AI-Codebase-Analyzer.git
cd AI-Codebase-Analyzer
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows**

```bash
.venv\Scripts\activate
```

**Mac/Linux**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn chromadb requests python-dotenv
```

### 4. Install Ollama

Download Ollama from:

```text
https://ollama.com
```

Then pull a model:

```bash
ollama pull llama3.1
```

Ollama runs locally at:

```text
http://localhost:11434
```

## Running the Project

### Start the FastAPI server

```bash
uvicorn app.main:app --reload --reload-dir app
```

Then open:

```text
http://127.0.0.1:8000
```

This launches the browser frontend.

## Usage

### Option A: Ingest a GitHub Repository from the UI

1. Open the frontend:

```text
http://127.0.0.1:8000
```

2. Paste a public GitHub repository URL into the **Ingest GitHub Repository** field
3. Click **Ingest Repo**
4. Wait for indexing to finish
5. Ask questions about the repository

Example repository URL:

```text
https://github.com/user/repo
```

### Option B: Ingest a Local Repository from the CLI

Run:

```bash
python app/ingest.py
```

Then enter a local folder path such as:

```text
C:\Projects\my-repository
```

This will:

- scan supported files
- chunk source text
- index chunks into ChromaDB
- generate a repository map

## Asking Questions

You can ask questions through:

- the browser frontend
- API endpoints
- FastAPI interactive docs

### Browser Interface

Open:

```text
http://127.0.0.1:8000
```

Example questions:

- Explain how this codebase works
- What are the main modules in this repository?
- Which file appears to be the main entry point?
- What technologies or frameworks does this project use?

### API Endpoints

#### JSON response with citations

```text
GET /ask?question=...
```

Example:

```text
http://127.0.0.1:8000/ask?question=Explain%20how%20this%20codebase%20works
```

Example response:

```json
{
  "answer": "This repository consists of ...",
  "sources": [
    {
      "path": ".repo_map.json",
      "chunk": "summary"
    },
    {
      "path": "server.js",
      "chunk": 0
    }
  ]
}
```

#### Streaming response

```text
GET /ask_stream?question=...
```

Returns a progressively streamed response for interactive use.

#### Repository map

```text
GET /repo_map
```

Returns the repository structure summary used to help answer architecture-level questions.

## Example Workflow

1. Install Ollama and pull a model
2. Start the FastAPI server
3. Open the browser UI
4. Ingest a GitHub repository
5. Ask questions about the codebase
6. Inspect cited source files in the response

## Technologies Used

- Python
- FastAPI
- ChromaDB
- Ollama
- LLaMA 3.1
- Vector embeddings / semantic retrieval
- Retrieval-Augmented Generation (RAG)

## Future Improvements

- Multi-repository indexing
- File preview panel for cited sources
- Better architecture summaries
- Support for additional programming languages
- Improved caching and prompt optimization
- Public demo deployment

## License

MIT License