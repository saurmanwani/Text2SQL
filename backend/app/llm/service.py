from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value
from app.db.models import WorkspaceSettings
from app.llm.client import LLMClient
from app.llm.providers import get_provider_preset
from app.settings import Settings


@dataclass(frozen=True, slots=True)
class ResolvedLLM:
    provider: str
    model: str
    client: LLMClient
    summaries_enabled: bool
    pii_redaction_enabled: bool


def resolve_llm(database: Session, settings: Settings) -> ResolvedLLM:
    workspace = database.get(WorkspaceSettings, 1)
    provider = workspace.llm_provider if workspace else settings.llm_provider
    preset = get_provider_preset(provider)
    model = (workspace.llm_model if workspace else settings.llm_model) or preset.default_model
    base_url = (workspace.llm_base_url if workspace else settings.llm_base_url) or preset.base_url
    encrypted_key = workspace.encrypted_llm_api_key if workspace else ""
    api_key = (
        decrypt_value(encrypted_key, settings.app_secret)
        if encrypted_key
        else settings.llm_api_key
    )
    cloud_summaries = (
        workspace.cloud_summaries_enabled if workspace else settings.cloud_summaries_enabled
    )
    pii_redaction = (
        workspace.pii_redaction_enabled if workspace else settings.pii_redaction_enabled
    )
    return ResolvedLLM(
        provider=provider,
        model=model,
        client=LLMClient(base_url, api_key, model),
        summaries_enabled=provider == "ollama" or cloud_summaries,
        pii_redaction_enabled=pii_redaction,
    )
