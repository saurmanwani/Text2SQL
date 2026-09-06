from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderPreset:
    base_url: str
    default_model: str
    requires_api_key: bool


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "ollama": ProviderPreset(
        base_url="http://localhost:11434/v1",
        default_model="qwen2.5-coder:7b",
        requires_api_key=False,
    ),
    "groq": ProviderPreset(
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        requires_api_key=True,
    ),
    "gemini": ProviderPreset(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.0-flash",
        requires_api_key=True,
    ),
    "openai": ProviderPreset(
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        requires_api_key=True,
    ),
}


def get_provider_preset(provider: str) -> ProviderPreset:
    try:
        return PROVIDER_PRESETS[provider.lower()]
    except KeyError as exc:
        supported = ", ".join(PROVIDER_PRESETS)
        raise ValueError(f"Unknown LLM provider. Supported providers: {supported}") from exc
