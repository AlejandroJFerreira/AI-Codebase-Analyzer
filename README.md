# AI Codebase Analyzer

An AI-powered tool that indexes a software repository and allows users to ask natural language questions about the codebase. The system retrieves relevant code snippets using vector search and generates explanations using a local LLM.

## Overview

AI Codebase Analyzer ingests a code repository, splits files into semantic chunks, and stores them in a vector database. When a user asks a question, the system retrieves the most relevant code segments and uses a language model to generate an answer grounded in the retrieved context.

This enables developers to quickly understand unfamiliar codebases, explore system architecture, and locate relevant implementation details.

## Features

* Natural language Q&A for codebases
* Vector search using **ChromaDB**
* Local LLM inference via **Ollama**
* Fast API interface built with **FastAPI**
* Chunked code ingestion for accurate retrieval
* Source references showing which files were used to generate answers
* Skips unnecessary directories (virtual environments, build folders, etc.)

## Architecture

```
Codebase → Ingestion → Chunking → ChromaDB (vector store)
                                ↓
                        Semantic Retrieval
                                ↓
User Question → FastAPI → Context Assembly → Ollama LLM → Answer
```

## Project Structure

```
ai-codebase-analyzer
│
├── app
│   ├── main.py        # FastAPI server
│   ├── ingest.py      # Codebase indexing script
│   ├── query.py       # Retrieval + LLM interaction
│   └── __init__.py
│
├── .chroma            # Local vector database (ignored in git)
├── .env               # Environment variables (ignored in git)
├── .gitignore
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/AlejandroJFerreira/AI-Codebase-Analyzer.git
cd ai-codebase-analyzer
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it:

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn chromadb requests python-dotenv
```

### 4. Install Ollama

Download and install Ollama:

https://ollama.com

Pull a model:

```bash
ollama pull llama3.1
```

Ollama will run locally on:

```
http://localhost:11434
```

## Usage

### 1. Index a repository

Run the ingestion script and provide the path to the repo you want to analyze.

```bash
python app/ingest.py
```

Example:

```
Enter path to codebase folder:
C:\Projects\my-repository
```

This will:

* Scan the repository
* Split files into chunks
* Store embeddings in ChromaDB

### 2. Start the API server

```bash
uvicorn app.main:app --reload --reload-dir app
```

Server runs at:

```
http://127.0.0.1:8000
```

### 3. Ask questions about the codebase

Open the interactive API docs:

```
http://127.0.0.1:8000/docs
```

Use the `/ask` endpoint with a question such as:

```
Explain how ingest.py works
```

Example response:

```json
{
  "answer": "Explanation of the code...",
  "sources": [
    {
      "path": "app/ingest.py",
      "chunk": 1
    }
  ]
}
```

## Technologies Used

* **Python**
* **FastAPI**
* **ChromaDB**
* **Ollama**
* **LLaMA 3.1**
* **Vector embeddings / semantic search**

## Future Improvements

* Streaming responses for faster UI feedback
* Web interface for interactive queries
* GitHub repository ingestion via URL
* Support for more programming languages
* Caching and performance optimizations
* Multi-repository indexing

## License

MIT License
