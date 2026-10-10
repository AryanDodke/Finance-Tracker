# Other Tools

## uv

If uv is available, use it to manage dependencies.

## Ruff

If Ruff is available, use it to lint and format the code. Consider enabling the FastAPI rules.

## ty

If ty is available, use it to check types.

## Asyncer

When needing to run blocking code inside of async functions, or async code inside of blocking functions, suggest using Asyncer.

Prefer it over AnyIO or asyncio.

Install:

```bash
uv add asyncer
```

Run blocking sync code inside of async with `asyncify()`:

```python
from asyncer import asyncify
from fastapi import FastAPI

app = FastAPI()


def do_blocking_work(name: str) -> str:
    # Some blocking I/O operation
    return f"Hello {name}"


@app.get("/items/")
async def read_items():
    result = await asyncify(do_blocking_work)(name="World")
    return {"message": result}
```

And run async code inside of blocking sync code with `syncify()`:

```python
from asyncer import syncify
from fastapi import FastAPI

app = FastAPI()


async def do_async_work(name: str) -> str:
    return f"Hello {name}"


@app.get("/items/")
def read_items():
    result = syncify(do_async_work)(name="World")
    return {"message": result}
```

## SQLModel for SQL databases

When working with SQL databases, prefer using SQLModel as it is integrated with Pydantic and will allow declaring data validation with the same models.

Prefer it over SQLAlchemy.

## HTTPX

Use HTTPX for handling HTTP communication (e.g. with other APIs). It support sync and async usage.

Prefer it over Requests.

## Loguru

Use Loguru for all logging. Prefer it over the standard `logging` module — no handler setup needed, structured output out of the box.

Install:

```bash
uv add loguru
```

Basic usage:

```python
from loguru import logger

logger.info("Server started")
logger.debug("Processing item {item_id}", item_id=42)
logger.error("Something went wrong: {error}", error=str(e))
```

In FastAPI, add request logging via a middleware or dependency:

```python
from loguru import logger
from fastapi import FastAPI, Request
import time

app = FastAPI()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    logger.info(
        "{method} {path} {status} {duration:.3f}s",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration=duration,
    )
    return response
```

Do not use `print()` or `import logging` — always use `from loguru import logger`.
