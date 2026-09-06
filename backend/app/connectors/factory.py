from app.connectors.sqlalchemy_connector import SQLAlchemyConnector
from app.core.crypto import decrypt_value
from app.db.models import DatabaseConnection
from app.settings import Settings


def connector_from_record(
    connection: DatabaseConnection,
    settings: Settings,
) -> SQLAlchemyConnector:
    url = decrypt_value(connection.encrypted_url, settings.app_secret)
    return SQLAlchemyConnector(url)
