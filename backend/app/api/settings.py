import os

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings


router = APIRouter()


class DeepSeekSettingsRequest(BaseModel):
    api_key: str = Field(min_length=1)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"


def _public_settings() -> dict[str, object]:
    settings = get_settings()
    return {
        "llm_mode": settings.llm_mode,
        "deepseek_base_url": settings.deepseek_base_url,
        "deepseek_model": settings.deepseek_model,
        "deepseek_api_key_configured": bool(settings.deepseek_api_key.strip()),
    }


@router.get("/model-settings")
def read_model_settings() -> dict[str, object]:
    return _public_settings()


@router.post("/model-settings/deepseek")
def update_deepseek_settings(payload: DeepSeekSettingsRequest) -> dict[str, object]:
    os.environ["LLM_MODE"] = "deepseek"
    os.environ["DEEPSEEK_API_KEY"] = payload.api_key.strip()
    os.environ["DEEPSEEK_BASE_URL"] = payload.base_url.strip() or "https://api.deepseek.com"
    os.environ["DEEPSEEK_MODEL"] = payload.model.strip() or "deepseek-v4-flash"
    get_settings.cache_clear()
    return _public_settings()
