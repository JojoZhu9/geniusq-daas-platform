import os
from typing import Literal, Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.domain.model_defaults import DEFAULT_DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL


router = APIRouter()


class DeepSeekSettingsRequest(BaseModel):
    api_key: str = Field(min_length=1)
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    model: str = DEFAULT_DEEPSEEK_MODEL


class ModelSettingsResponse(BaseModel):
    llm_mode: str
    deepseek_base_url: str
    deepseek_model: str
    deepseek_api_key_configured: bool
    deepseek_api_key_masked: str = ""


class DeepSeekConnectionResponse(BaseModel):
    ok: bool
    mode: str
    message: str
    error_type: Optional[Literal[
        "missing_api_key",
        "timeout",
        "auth_error",
        "rate_limited",
        "network_error",
        "provider_error",
    ]] = None


def _mask_key(api_key: str) -> str:
    cleaned = api_key.strip()
    if not cleaned:
        return ""
    if len(cleaned) <= 8:
        return f"{cleaned[:2]}-****"
    return f"{cleaned[:3]}****{cleaned[-4:]}"


def _public_settings() -> ModelSettingsResponse:
    settings = get_settings()
    api_key = settings.deepseek_api_key.strip()
    return ModelSettingsResponse(
        llm_mode=settings.llm_mode,
        deepseek_base_url=settings.deepseek_base_url,
        deepseek_model=settings.deepseek_model,
        deepseek_api_key_configured=bool(api_key),
        deepseek_api_key_masked=_mask_key(api_key),
    )


@router.get("/model-settings")
def read_model_settings() -> ModelSettingsResponse:
    return _public_settings()


@router.post("/model-settings/deepseek")
def update_deepseek_settings(payload: DeepSeekSettingsRequest) -> ModelSettingsResponse:
    os.environ["LLM_MODE"] = "deepseek"
    os.environ["DEEPSEEK_API_KEY"] = payload.api_key.strip()
    os.environ["DEEPSEEK_BASE_URL"] = payload.base_url.strip() or DEFAULT_DEEPSEEK_BASE_URL
    os.environ["DEEPSEEK_MODEL"] = payload.model.strip() or DEFAULT_DEEPSEEK_MODEL
    get_settings.cache_clear()
    return _public_settings()


@router.post("/model-settings/deepseek/test")
def test_deepseek_connection() -> DeepSeekConnectionResponse:
    settings = get_settings()
    api_key = settings.deepseek_api_key.strip()
    if not api_key:
        return DeepSeekConnectionResponse(
            ok=False,
            mode=settings.llm_mode or "offline",
            error_type="missing_api_key",
            message="尚未配置 DeepSeek API Key，可继续使用离线模式。",
        )

    base_url = settings.deepseek_base_url.rstrip("/") or DEFAULT_DEEPSEEK_BASE_URL
    try:
        with httpx.Client(timeout=settings.deepseek_timeout_seconds) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": settings.deepseek_model or DEFAULT_DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 8,
                    "temperature": 0,
                },
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        return DeepSeekConnectionResponse(
            ok=False,
            mode=settings.llm_mode,
            error_type="timeout",
            message="DeepSeek 连接测试超时，请检查网络或稍后重试。",
        )
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        if status_code in (401, 403):
            return DeepSeekConnectionResponse(
                ok=False,
                mode=settings.llm_mode,
                error_type="auth_error",
                message="DeepSeek 鉴权失败，请检查 API Key 是否正确。",
            )
        if status_code == 429:
            return DeepSeekConnectionResponse(
                ok=False,
                mode=settings.llm_mode,
                error_type="rate_limited",
                message="DeepSeek 请求被限流，请稍后重试。",
            )
        return DeepSeekConnectionResponse(
            ok=False,
            mode=settings.llm_mode,
            error_type="provider_error",
            message=f"DeepSeek 服务返回异常状态码：{status_code}。",
        )
    except httpx.HTTPError:
        return DeepSeekConnectionResponse(
            ok=False,
            mode=settings.llm_mode,
            error_type="network_error",
            message="DeepSeek 网络连接失败，请检查 Base URL 和本地网络。",
        )

    return DeepSeekConnectionResponse(ok=True, mode="deepseek", message="DeepSeek 连接测试成功。")
