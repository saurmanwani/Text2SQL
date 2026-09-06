from time import perf_counter

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.client import LLMClient
from app.llm.providers import get_provider_preset
from app.llm.service import resolve_llm
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/llm", tags=["llm"])


class LLMStatusResponse(BaseModel):
    provider: str
    model: str
    reachable: bool
    latency_ms: int


def build_llm_client(settings: Settings) -> LLMClient:
    preset = get_provider_preset(settings.llm_provider)
    return LLMClient(
        base_url=settings.llm_base_url or preset.base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model or preset.default_model,
    )


@router.get("/status", response_model=LLMStatusResponse)
async def llm_status(
    database: Session = Depends(get_db),
) -> LLMStatusResponse:
    settings = get_settings()
    resolved = resolve_llm(database, settings)
    client = resolved.client
    started_at = perf_counter()
    reachable = await client.is_reachable()
    latency_ms = round((perf_counter() - started_at) * 1000)

    return LLMStatusResponse(
        provider=resolved.provider,
        model=client.model,
        reachable=reachable,
        latency_ms=latency_ms,
    )
