from uuid import UUID, uuid4

from sqlmodel import Session

from app.models.logging.request import RequestLog, RequestLogUpdate, RequestStatus
from app.utils import now

class RequestLogCrud:
    def __init__(self, session: Session):
        self.session = session

    def create(self, request_id: UUID, input_text: str) -> RequestLog:
        create_request_log = RequestLog(
            request_id=request_id,
            request_text=input_text,
        )
        self.session.add(create_request_log)
        self.session.commit()
        self.session.refresh(create_request_log)
        return create_request_log

    def update(self, request_log_id: UUID, request_status: RequestStatus, request_log_update: RequestLogUpdate):
        request_log = self.session.get(RequestLog, request_log_id)
        if not request_log:
            raise ValueError(f"Request Log not found for id {request_log_id}")
        
        update_data = request_log_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(request_log, field, value)

        request_log.updated_at = now()
        request_log.status = request_status
        self.session.add(request_log)
        self.session.commit()
        self.session.refresh(request_log)

        return request_log

    def get(self, request_log_id: UUID) -> RequestLog | None:
        return self.session.get(RequestLog, request_log_id)