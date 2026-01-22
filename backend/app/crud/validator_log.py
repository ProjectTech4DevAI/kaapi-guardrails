from uuid import UUID, uuid4

from sqlmodel import Session

from app.models.logging.validator import ValidatorLog
from app.utils import now

class ValidatorLogCrud:
    def __init__(self, session: Session):
        self.session = session

    def create(self, log: ValidatorLog) -> ValidatorLog:
        log.updated_at = now()
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log
