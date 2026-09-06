from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def write_audit_event(database: Session, **values: object) -> AuditEvent:
    event = AuditEvent(**values)
    database.add(event)
    database.commit()
    database.refresh(event)
    return event
