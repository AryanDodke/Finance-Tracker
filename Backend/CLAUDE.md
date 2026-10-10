# Spend Analyser

Personal finance tracker focused on strict truth reconciliation between SBI bank statements (the source of truth) and Apple Notes (supplementary context).

## Development Setup

We use `uv` for lightning-fast package management and virtual environments.

1. **Create Virtual Environment & Install Dependencies:**
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   uv pip install -r requirements.txt
   uv pip install status  # HTTP status codes
   ```

2. **Run Backend (FastAPI):**
   ```bash
   cd Backend
   fastapi dev main.py
   ```
   Or using uvicorn directly:
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Run Frontend (Vite/React):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Code Quality Standards

We strictly adhere to the project's code quality and FastAPI standards (refer to `.skills/code-quality/SKILL.md` and `.skills/fastapi-skill/SKILL.md`).

- **Formatting & Linting:** 
  We use `ruff` to enforce PEP8 standards.
  ```bash
  ruff check --fix app/ main.py
  ruff format app/ main.py
  ```
- **FastAPI Best Practices:** 
  - Use `Annotated` for parameter and dependency declarations (e.g., `SessionDep = Annotated[Session, Depends(get_session)]`).
  - Do not use Pydantic `RootModel`.
  - Always use named constants from the `status` library for HTTP response codes.
- **Exception Handling:** Always use `raise Exception from err` inside `except` blocks.
- **Testing:** `pytest` is used for unit and integration testing. Maintain a minimum of 80% coverage.

## Project Structure

- **Backend/app/api/routers/**: FastAPI endpoints (Upload, Transactions, Review, Insights, Reconcile, Chat).
- **Backend/app/src/services/**: Core business logic (Parsing, Normalisation, Categorisation, LLM Gateway).
- **Backend/app/src/models/**: SQLAlchemy database ORM definitions.
- **frontend/src/**: React frontend using Vite, styled with vanilla CSS (glassmorphism UI, Recharts).
