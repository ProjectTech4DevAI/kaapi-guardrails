from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.enum import LLMValidatorName
from app.models.config.llm_prompt_config import LLMPromptConfig
from app.utils import now


class LLMPromptConfigCrud:
    def create(
        self,
        session: Session,
        payload,
        organization_id: int,
        project_id: int,
    ) -> LLMPromptConfig:
        obj = LLMPromptConfig(
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
                "A prompt config with the same configuration already exists",
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
    ) -> LLMPromptConfig:
        query = select(LLMPromptConfig).where(
            LLMPromptConfig.id == id,
            LLMPromptConfig.organization_id == organization_id,
            LLMPromptConfig.project_id == project_id,
        )
        obj = session.exec(query).first()
        if not obj:
            raise HTTPException(404, "LLM prompt config not found")
        return obj

    def list(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        validator_name: Optional[LLMValidatorName] = None,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> List[LLMPromptConfig]:
        query = select(LLMPromptConfig).where(
            LLMPromptConfig.organization_id == organization_id,
            LLMPromptConfig.project_id == project_id,
        )

        if validator_name is not None:
            query = query.where(LLMPromptConfig.validator_name == validator_name)

        query = query.order_by(LLMPromptConfig.created_at, LLMPromptConfig.id)

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
        payload,
    ) -> LLMPromptConfig:
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
                "A prompt config with the same configuration already exists",
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(obj)
        return obj

    def delete(self, session: Session, obj: LLMPromptConfig) -> None:
        session.delete(obj)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise


llm_prompt_config_crud = LLMPromptConfigCrud()
