---
name: code-quality
description: Use when writing, reviewing, or modifying any Python backend code in this project. Enforces naming conventions, comments, PEP8, linting, test coverage, and backend best practices.
---

# Code Quality Standards

Mandatory standards for all Python code written in this project. No exceptions.

---

## 1. Naming Conventions

### Variables and Parameters — Always Verbose

Single-character names are **never** allowed, except loop counters in pure numeric iterations.

```python
# ❌ WRONG
def get(u, t):
    r = db.find(u)
    return r

# ✅ CORRECT
def get_user_by_token(user_id: str, auth_token: str) -> UserModel:
    user_record = db.find(user_id)
    return user_record
```

| Context | Bad | Good |
|---|---|---|
| Response variable | `r`, `res` | `response`, `api_response` |
| Database result | `d`, `db_r` | `db_result`, `query_result` |
| Loop index | `i`, `j` | `index`, `item_index` (or `i` only in `for i in range(n)`) |
| Exception | `e` | `error`, `exc`, `validation_error` |
| Temporary | `tmp`, `t` | `temp_user_data`, `staging_payload` |
| Count | `n`, `c` | `total_count`, `retry_count` |

**Function and method names** must describe what they do:
```python
# ❌ WRONG
def process(data): ...
def handle(req): ...

# ✅ CORRECT
def process_chat_request(chat_payload: ChatRequest): ...
def handle_authentication_failure(request: Request): ...
```

---

## 2. Docstrings for All Functions and Classes

Every function, method, and class **must** have a docstring using triple quotes (`""" """`). Use `#` only for inline clarifications on a single line of logic.

```python
# ❌ WRONG — no docstring, or plain # comment used as substitute
def calculate_token_count(text: str) -> int:
    # count tokens
    return len(text.split())

# ✅ CORRECT — docstring explains intent, parameters, and non-obvious decisions
def calculate_token_count(text: str) -> int:
    """Approximate token count by whitespace splitting.

    OpenAI's tiktoken is more accurate but adds latency on hot paths;
    this heuristic is used for pre-flight budget checks only.
    """
    return len(text.split())
```

**Class example:**

```python
class ChatService:
    """Orchestrates chat session creation and LLM invocation.

    Coordinates between ChatDAO (persistence), PromptBuilder (prompt assembly),
    and ModelInvocationService (LLM calls). Does not hold state between requests.
    """

    def get_response(self, session_id: str, user_message: str) -> ChatResponse:
        """Fetch an LLM response for a given session and user message.

        Args:
            session_id: Active chat session identifier.
            user_message: Latest message from the user.

        Returns:
            ChatResponse with the assistant's reply and updated session metadata.

        Raises:
            SessionNotFoundError: If session_id does not exist in the DB.
            LLMInvocationError: If the upstream model call fails.
        """
        ...
```

**Rules:**
- Triple-quoted docstring on every function, method, and class — no exceptions
- First line: one-sentence summary of what it does
- For non-trivial functions: add `Args:`, `Returns:`, `Raises:` sections
- Mark workarounds inline with `# TODO(reason):` or `# WORKAROUND:` on the relevant line
- Do **not** state the obvious: `"""Increments count."""` above `count += 1` is noise

---

## 3. PEP8 Compliance

All code **must** pass Ruff with zero errors. Ruff enforces PEP8 and more.

### Enforcement

```bash
# Check
ruff check app/

# Auto-fix safe issues
ruff check --fix app/

# Format
ruff format app/
```

### Key PEP8 Rules

```python
# ❌ WRONG
def build_prompt(system_message,user_message,history=[]):
    result={"system":system_message,"user":user_message}
    return result

# ✅ CORRECT
def build_prompt(
    system_message: str,
    user_message: str,
    history: list[dict] | None = None,
) -> dict:
    # Build the prompt payload for LLM invocation.
    # history defaults to None (not mutable default) to avoid shared state bugs.
    history = history or []
    return {"system": system_message, "user": user_message, "history": history}
```

- Max line length: **88** characters (Ruff default)
- No mutable default arguments (`[]`, `{}`) — use `None` and initialise inside
- Two blank lines between top-level definitions
- Type annotations on all function signatures
- Imports: stdlib → third-party → local, each group separated by a blank line

### Ruff Config (add to `pyproject.toml` if not present)

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B"]
```

---

## 4. Linting — Zero Tolerance

Code must pass linting with **zero errors and zero warnings** before being considered complete.

```bash
# Must exit with code 0
ruff check app/ && echo "PASSED"
```

**Red flags that must be fixed, not suppressed:**

| Issue | Fix |
|---|---|
| Unused import | Remove it |
| Undefined variable | Fix the bug |
| Shadowed built-in | Rename (`type_` not `type`, `id_` not `id`) |
| Bare `except:` | Catch specific exceptions |
| `print()` in production code | Replace with `logger.info/debug/error` |

Only suppress with `# noqa: <code>` when the rule is provably wrong for that line, with a comment explaining why.

---

## 5. Test Coverage

**Minimum coverage: 80%.** PRs below 80% are not complete.

```bash
# Run tests with coverage
pytest app/test/ --cov=app --cov-report=term-missing --cov-fail-under=80
```

### When a Feature Is Added or Modified

Tests **must** be updated in the same change. No feature lands without corresponding test coverage.

**Checklist for every feature change:**
- [ ] New functions → new test cases in `app/test/test_<feature>.py`
- [ ] Changed function signature or behaviour → existing tests updated
- [ ] New edge cases introduced → test the happy path AND the failure path
- [ ] New DAO method → test with mocked DB
- [ ] New service method → test business logic in isolation

```python
# ✅ Example — test both success and failure paths
class TestGetUserById:
    def test_returns_user_when_found(self, mock_db):
        # Arrange: seed a known user record
        expected_user = UserModel(id="123", name="Alice")
        mock_db.find.return_value = expected_user

        result = get_user_by_id(user_id="123", db=mock_db)

        assert result == expected_user

    def test_raises_not_found_when_user_missing(self, mock_db):
        # Arrange: simulate empty DB result
        mock_db.find.return_value = None

        with pytest.raises(UserNotFoundError):
            get_user_by_id(user_id="nonexistent", db=mock_db)
```

---

## 6. Backend Best Practices

### Error Handling

```python
# ❌ WRONG — swallows errors silently
try:
    result = call_llm(prompt)
except Exception:
    pass

# ✅ CORRECT — catch specifically, log, re-raise or return structured error
try:
    llm_response = call_llm(prompt)
except OpenAIRateLimitError as rate_limit_error:
    logger.warning("LLM rate limit hit, backing off: {error}", error=str(rate_limit_error))
    raise ServiceUnavailableError("LLM rate limit exceeded") from rate_limit_error
```

- Never use bare `except:` or `except Exception: pass`
- Always use `raise X from original_error` to preserve traceback
- Return structured error responses from API layer, not raw exception messages

### Logging — Loguru Only

```python
from loguru import logger

# ✅ Use structured key=value style for machine-parseable logs
logger.info("Chat request received", user_id=user_id, session_id=session_id)
logger.error("DB query failed: {error}", error=str(db_error))

# ❌ Never use print() or import logging
print("Processing...")          # WRONG
import logging; logging.info()  # WRONG
```

### HTTP Status Codes — `status` Library Only

```python
from status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

# ✅ Always use named constants
@router.post("/chat", status_code=HTTP_201_CREATED)
async def create_chat_session(...): ...

# ❌ Never use raw integers
@router.post("/chat", status_code=201): ...  # WRONG
```

### Async Discipline

```python
# ✅ async only when calling awaitable code
async def fetch_embeddings(text: str) -> list[float]:
    return await openai_client.embed(text)

# ✅ sync for blocking I/O (FastAPI runs it in threadpool automatically)
def load_static_prompt(prompt_name: str) -> str:
    return Path(f"app/data/prompts/{prompt_name}.txt").read_text()

# ❌ async with blocking I/O blocks the event loop
async def load_static_prompt(prompt_name: str) -> str:
    return Path(...).read_text()  # WRONG — blocks event loop
```

### Constants and Raw Literals

All magic strings, magic numbers, and repeated raw literals **must** be defined as named constants in `app/utils/utils.py`. Never scatter raw literals across the codebase.

```python
# ❌ WRONG — raw literals inline
@router.post("/chat")
async def create_chat(payload: ChatRequest):
    if len(payload.message) > 4096:
        raise ValueError("Message too long")
    model_name = "gpt-4o"
    ...

# ✅ CORRECT — constants defined in app/utils/utils.py and imported
# app/utils/utils.py
MAX_MESSAGE_LENGTH: int = 4096
DEFAULT_LLM_MODEL: str = "gpt-4o"
CHAT_COLLECTION_NAME: str = "chat_sessions"
DEFAULT_EMBEDDING_DIMENSIONS: int = 1536

# app/api/routers/chat.py
from app.utils.utils import MAX_MESSAGE_LENGTH, DEFAULT_LLM_MODEL

@router.post("/chat")
async def create_chat(payload: ChatRequest):
    """Handle incoming chat request and invoke the LLM."""
    if len(payload.message) > MAX_MESSAGE_LENGTH:
        raise ValueError("Message exceeds maximum allowed length")
    ...
```

**What belongs in `app/utils/utils.py`:**

| Type | Examples |
|---|---|
| Size/length limits | `MAX_MESSAGE_LENGTH`, `MAX_HISTORY_TURNS` |
| Model identifiers | `DEFAULT_LLM_MODEL`, `DEFAULT_EMBEDDING_MODEL` |
| Collection/index names | `CHAT_COLLECTION_NAME`, `VECTOR_INDEX_NAME` |
| Timeout values | `LLM_REQUEST_TIMEOUT_SECONDS` |
| Default config values | `DEFAULT_TOP_K`, `DEFAULT_TEMPERATURE` |
| Error/status strings | `ERROR_SESSION_NOT_FOUND` |

**Rules:**
- Use `UPPER_SNAKE_CASE` for all constants
- Add a type annotation: `MAX_RETRIES: int = 3`
- Group related constants with a blank line and a `#` section comment
- If a constant is only used in one module, it may live in that module — but shared constants always go in `utils.py`

### Secrets and Config

- Never hardcode API keys, URLs, or credentials — always load from settings
- All config goes through `app/core/setting.py`
- No `os.environ.get("KEY")` scattered across modules — use the settings object

---

## Quick Reference — Pre-Commit Checklist

Before marking any task complete:

```
[ ] Variable and function names are verbose and descriptive
[ ] Every function, method, and class has a triple-quoted docstring
[ ] Non-trivial functions include Args/Returns/Raises in docstring
[ ] All magic strings and numbers extracted to app/utils/utils.py as UPPER_SNAKE_CASE constants
[ ] ruff check app/ exits with 0 errors
[ ] ruff format app/ applied
[ ] pytest --cov=app --cov-fail-under=80 passes
[ ] Tests added/updated for all changed behaviour
[ ] No print() — only logger.*
[ ] No raw status integers — only status library constants
[ ] No bare except: or swallowed exceptions
[ ] No hardcoded secrets or config values
```
