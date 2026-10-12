# 🤖 AI Job Application Agent

An agent that takes a **CV + job description**, matches skills using embeddings and a vector
database, identifies gaps, and uses an LLM agent graph to generate a **tailored CV**, a
**cover letter**, and **interview prep questions**.

## Architecture

```
                 ┌──────────────┐
                 │ Job Posting  │
                 └──────┬───────┘
                        ↓
CV ─────────────→ Document Parser
                        ↓
                 Embedding Model  (Sentence-Transformers)
                        ↓
                 Vector Database  (ChromaDB)
                        ↓
                ┌───────────────┐
                │ Matching Agent│
                └───────┬───────┘
                        ↓
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
      Skill Match   Missing Skills   Experience
          ↓             ↓             ↓
          └─────────────┼─────────────┘
                        ↓
                LangGraph LLM Agent
                        ↓
       ┌────────────────┼───────────────┐
       ↓                ↓               ↓
 Tailored CV       Cover Letter    Interview Prep
```

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI + Uvicorn |
| Agent orchestration | LangGraph |
| Vector store | NumPy cosine similarity (zero C++ dependencies) |
| Embeddings | `scikit-learn` TF-IDF (fallback) / `sentence-transformers` (if available) |
| LLM | OpenRouter via its OpenAI-compatible API (pluggable) |
| Relational DB | SQLite (local dev, auto-created) / PostgreSQL (production) |
| Containerization | Docker / docker-compose |
| Frontend | Plain HTML/CSS/JS |

## How it works

1. **Document Parser** (`app/parsers/document_parser.py`) extracts text from the uploaded
   CV (PDF/DOCX/TXT) and chunks both the CV and job description into semantically
   meaningful pieces.
2. **Embedding Model** (`app/embeddings/embedder.py`) embeds CV chunks with
   Sentence-Transformers.
3. **Vector Database** (`app/vectorstore/store.py`) stores CV chunk embeddings in a
   per-application ChromaDB collection.
4. **Matching Agent** (`app/agents/nodes.py::match_skills_node`) extracts the JD's concrete
   requirements (via LLM), embeds each requirement, and retrieves the most similar CV
   chunk via the vector database to score it as a strong / partial / missing match.
5. **LangGraph LLM Agent** (`app/agents/graph.py`) fans out into three parallel nodes that
   each call the LLM: a tailored CV section generator, a cover letter generator, and an
   interview-prep question generator — all grounded in the actual match/gap data so
   nothing is fabricated.
6. Results are persisted to Postgres/SQLite and served to the frontend, which polls for
   completion and renders the report.

## Running locally (no Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or on Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env from .env.example and add your OpenRouter API key:
cp ../.env.example .env

# Start the server:
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` directly in your browser — the FastAPI backend now automatically mounts and serves the full interactive frontend!

## Running with Docker

```bash
cp .env.example .env
# edit .env with your API key

docker compose up --build
```

Visit `http://localhost:8000` — the backend also serves the frontend directly.

## API

- `POST /api/applications` — multipart form: `cv_file`, `job_title` (optional),
  `job_description`. Returns `{ id, status }` and kicks off the agent pipeline as a
  background task.
- `GET /api/applications/{id}` — poll for status/results (`pending` → `processing` →
  `complete`/`failed`).
- `GET /api/applications` — list recent applications.
- `GET /api/health` — health check.

## Project layout

```
backend/
  app/
    main.py                # FastAPI app
    config.py               # Settings (env-driven)
    database.py, models.py, schemas.py
    parsers/document_parser.py     # PDF/DOCX/TXT parsing + chunking
    embeddings/embedder.py          # Sentence-Transformers wrapper
    vectorstore/store.py            # ChromaDB wrapper
    llm/client.py                    # Anthropic/OpenAI wrapper
    agents/
      prompts.py             # Prompt templates
      nodes.py                # Individual LangGraph node functions
      graph.py                 # StateGraph wiring (fan-out/fan-in)
    routers/application.py    # REST endpoints
  requirements.txt
  Dockerfile
frontend/
  index.html, style.css, app.js
docker-compose.yml
.env.example
```

## Notes / extending this project

- **Swap FAISS in for Chroma**: only `app/vectorstore/store.py` needs to change — the
  rest of the pipeline calls `add_cv_chunks` / `query_similar` and doesn't know which
  vector store is behind them.
- **Swap LLM providers**: set `LLM_PROVIDER=openai` in `.env`; `app/llm/client.py` is the
  only file that talks to a provider SDK.
- **Anti-hallucination**: every generation prompt (tailored CV, cover letter, interview
  prep) is given the *actual* matched evidence and gaps computed by the embedding-based
  Matching Agent, and is explicitly instructed not to invent experience — this is the
  difference between this project and "just calling an LLM API".
- **Production hardening ideas**: move `_process_application` to a real task queue
  (Celery/RQ) instead of `BackgroundTasks`, add Alembic migrations, add auth, rate-limit
  uploads, and add streaming responses for long LLM generations.
