# genai_be_boilerplate

## Project Overview

A boilerplate backend for GenAI projects, organized for modularity and scalability. Built with FastAPI, MongoDB, Qdrant, and OpenAI-compatible LLMs/embedders.

## Structure & Purpose

- `app/`

  - `api/`: FastAPI route handlers and shared dependencies.
    - `routers/`: One file per feature (e.g. `chat.py`). Router-level config (prefix, tags) goes on the `APIRouter` itself.
    - `dependencies.py`: Shared dependencies (auth, DB connections, etc.).

  - `core/`: Global configuration.
    - `config.yaml`: Static config values.
    - `setting.py`: Loads `.env` and exposes settings.

  - `data/`
    - `files/`: Static data files (CSVs, text, etc.).
    - `prompts/`: Prompt templates and prompt-building logic for LLMs.

  - `src/`: Main backend logic.
    - `dao/`: Database access objects.
      - `mongo/`: MongoDB DAOs — new DAOs extend `base_dao.py`.
      - `vectordb/`: Vector DB access (Qdrant).
    - `dto/`: Pydantic schemas for API request/response validation.
    - `language_models/`: LLM and embedding wrappers.
      - `llm/`: LLM clients — new clients extend `base_llm.py`.
      - `embedders/`: Embedding clients — extend `base_embedding.py`.
    - `models/`: Core internal data models.
    - `services/`: Business logic layer.
      - `model_invocation.py`: LLM execution logic.
      - Feature services (e.g. `chat.py`) orchestrate DAOs and model invocation.
    - `utils/`: Shared helpers — `logger.py` (Loguru), `chat.py`.

  - `test/`: All tests, mirroring `src/` structure (e.g. `test_chat.py`).

- `main.py`: FastAPI app entry point — registers all routers.
- `requirements.txt`: Python dependencies (use only if not using uv).
- `Dockerfile` & `docker-compose.yml`: Containerization and orchestration.

## Setup

### Using uv (recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Add a new dependency
uv add <package>

# Add a dev-only dependency
uv add --dev <package>
```

### Using pip

```bash
pip install -r requirements.txt
```

## Running the API

```bash
# Development (with reload)
fastapi dev

# Or via uvicorn
uvicorn main:app --reload

# Production
fastapi run
```

## Running Tests

```bash
# All tests
pytest app/test/

# Single test file
pytest app/test/test_chat.py

# With output
pytest app/test/ -v
```

## Docker

```bash
docker-compose up --build
```

## Conventions

- **Status codes**: use the `status` library (`from status import HTTP_200_OK`) — never raw integers.
- **Logging**: use Loguru (`from loguru import logger`) — never `print()` or `import logging`.
- **HTTP clients**: use HTTPX over Requests.
- **Async**: use `async def` only when calling `await`-able code; default to `def` otherwise.

## Adding a New Feature

1. `app/src/dto/<feature>.py` — request/response schemas
2. `app/src/models/<feature>.py` — internal data models
3. `app/data/prompts/<feature>.py` — prompt templates
4. `app/src/dao/mongo/<feature>.py` — DB access (extend `base_dao.py`)
5. `app/src/services/<feature>.py` — business logic
6. `app/api/routers/<feature>.py` — route handlers, register in `main.py`
7. `app/test/test_<feature>.py` — tests
