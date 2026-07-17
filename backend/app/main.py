from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.chat import router as chat_router
from .api.dashboards import router as dashboards_router
from .api.datasource import router as datasource_router
from .api.knowledge import router as knowledge_router
from .api.requirements import router as requirements_router
from .api.settings import router as settings_router
from .config import get_settings
from .db import init_database
from .errors import ApiError


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="GeniusQ DaaS Platform Intelligent Query Demo", lifespan=lifespan)
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(knowledge_router, prefix="/api", tags=["knowledge"])
app.include_router(dashboards_router, prefix="/api", tags=["dashboards"])
app.include_router(datasource_router, prefix="/api", tags=["datasource"])
app.include_router(requirements_router, prefix="/api", tags=["requirements"])
app.include_router(settings_router, prefix="/api", tags=["settings"])


@app.exception_handler(ApiError)
def api_error_handler(_: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content=error.payload)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": get_settings().llm_mode}
