from uuid import UUID, uuid4

from sqlmodel import Session

from app.models.logging.validator import ValidatorLog, ValidatorOutcome
from app.utils import now

class ValidatorLogCrud:
    def __init__(self, session: Session):
        self.session = session

    def create(self, request_id: UUID, name: str, input: str, output: str, error: str, outcome: ValidatorOutcome) -> ValidatorLog:
        create_validator_log = ValidatorLog(
            request_id=request_id,
            name=name,
            input=input,
            output=output,
            error=error,
            outcome=outcome,
        )
        create_validator_log.updated_at = now()
        self.session.add(create_validator_log)
        self.session.commit()
        self.session.refresh(create_validator_log)
        return create_validator_log
