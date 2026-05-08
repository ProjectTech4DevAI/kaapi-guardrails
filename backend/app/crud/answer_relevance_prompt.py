from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.config.answer_relevance_prompt import AnswerRelevancePrompt
from app.schemas.answer_relevance_prompt import (
    AnswerRelevancePromptCreate,
    AnswerRelevancePromptUpdate,
)
from app.utils import now


class AnswerRelevancePromptCrud:
    def create(
        self,
        session: Session,
        payload: AnswerRelevancePromptCreate,
        organization_id: int,
        project_id: int,
    ) -> AnswerRelevancePrompt:
        obj = AnswerRelevancePrompt(
            **payload.model_dump(),
            organization_id=organization_id,
            project_id=project_id,
        )
        session.add(obj)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400,
                "Answer relevance prompt with the same configuration already exists",
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(obj)
        return obj

    def get(
        self,
        session: Session,
        id: UUID,
        organization_id: int,
        project_id: int,
    ) -> AnswerRelevancePrompt:
        query = select(AnswerRelevancePrompt).where(
            AnswerRelevancePrompt.id == id,
            AnswerRelevancePrompt.organization_id == organization_id,
            AnswerRelevancePrompt.project_id == project_id,
        )
        obj = session.exec(query).first()
        if not obj:
            raise HTTPException(404, "Answer relevance prompt not found")
        return obj

    def list(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        offset: int = 0,
        limit: int | None = None,
    ) -> List[AnswerRelevancePrompt]:
        query = (
            select(AnswerRelevancePrompt)
            .where(
                AnswerRelevancePrompt.organization_id == organization_id,
                AnswerRelevancePrompt.project_id == project_id,
            )
            .order_by(AnswerRelevancePrompt.created_at, AnswerRelevancePrompt.id)
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return list(session.exec(query).all())

    def update(
        self,
        session: Session,
        id: UUID,
        organization_id: int,
        project_id: int,
        payload: AnswerRelevancePromptUpdate,
    ) -> AnswerRelevancePrompt:
        obj = self.get(session, id, organization_id, project_id)

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(obj, key, value)

        obj.updated_at = now()
        session.add(obj)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400,
                "Answer relevance prompt with the same configuration already exists",
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(obj)
        return obj

    def delete(self, session: Session, obj: AnswerRelevancePrompt) -> None:
        session.delete(obj)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise


answer_relevance_prompt_crud = AnswerRelevancePromptCrud()
