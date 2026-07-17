import os

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings


router = APIRouter()


class DeepSeekSettingsRequest(BaseModel):
    api_key: str = Field(min_length=1)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"


def _mask_key(api_key: str) -> str:
    cleaned = api_key.strip()
    if not cleaned:
        return ""
    if len(cleaned) <= 8:
        return f"{cleaned[:2]}-****"
    return f"{cleaned[:3]}****{cleaned[-4:]}"


def _public_settings() -> dict[str, object]:
    settings = get_settings()
    api_key = settings.deepseek_api_key.strip()
    return {
        "llm_mode": settings.llm_mode,
        "deepseek_base_url": settings.deepseek_base_url,
        "deepseek_model": settings.deepseek_model,
        "deepseek_api_key_configured": bool(api_key),
        "deepseek_api_key_masked": _mask_key(api_key),
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


@router.post("/model-settings/deepseek/test")
def test_deepseek_connection() -> dict[str, object]:
    settings = get_settings()
    api_key = settings.deepseek_api_key.strip()
    if not api_key:
        return {
            "ok": False,
            "mode": settings.llm_mode or "offline",
            "message": "尚未配置 DeepSeek API Key，可继续使用离线模式。",
        }

    base_url = settings.deepseek_base_url.rstrip("/") or "https://api.deepseek.com"
    try:
        with httpx.Client(timeout=settings.deepseek_timeout_seconds) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": settings.deepseek_model or "deepseek-chat",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 8,
                    "temperature": 0,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as error:
        return {
            "ok": False,
            "mode": settings.llm_mode,
            "message": f"DeepSeek 连接测试失败：{error.__class__.__name__}",
        }

    return {
        "ok": True,
        "mode": "deepseek",
        "message": "DeepSeek 连接测试成功。",
    }
