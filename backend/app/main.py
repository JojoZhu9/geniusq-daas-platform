from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .db import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="极智 DAAS 智能问数优化 Demo", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": get_settings().llm_mode}
