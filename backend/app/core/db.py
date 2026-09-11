from sqlmodel import Session, create_engine, select

from app.core.config import settings

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# All SQLModel models must be imported (app.models) before this, or relationship
# initialization can fail: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables are created via Alembic migrations, not here.
    pass
