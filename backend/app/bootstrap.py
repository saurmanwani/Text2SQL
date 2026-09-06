from sqlalchemy import func, select

from app.core.crypto import encrypt_value
from app.db.models import DatabaseConnection, WorkspaceSettings
from app.db.session import SessionLocal, init_db
from app.settings import get_settings
from sample_data.seed import seed_database


def bootstrap_application() -> None:
    settings = get_settings()
    sample_database = seed_database().resolve()
    init_db()
    with SessionLocal() as database:
        if database.scalar(select(func.count(DatabaseConnection.id))) == 0:
            url = f"sqlite:///{sample_database}"
            database.add(
                DatabaseConnection(
                    name="Demo (SQLite)",
                    dialect="sqlite",
                    encrypted_url=encrypt_value(url, settings.app_secret),
                    read_only_status="unknown",
                )
            )
        if database.get(WorkspaceSettings, 1) is None:
            database.add(
                WorkspaceSettings(
                    id=1,
                    llm_provider=settings.llm_provider,
                    llm_model=settings.llm_model,
                    encrypted_llm_api_key=(
                        encrypt_value(settings.llm_api_key, settings.app_secret)
                        if settings.llm_api_key
                        else ""
                    ),
                    llm_base_url=settings.llm_base_url,
                    cloud_summaries_enabled=settings.cloud_summaries_enabled,
                    pii_redaction_enabled=settings.pii_redaction_enabled,
                )
            )
        database.commit()
