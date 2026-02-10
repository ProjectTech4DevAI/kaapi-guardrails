from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.enum import Stage, ValidatorType
from app.models.config.validator_config import ValidatorConfig
from app.schemas.validator_config import ValidatorCreate
from app.utils import now, split_validator_payload


class ValidatorConfigCrud:
    def create(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        payload: ValidatorCreate,
    ) -> dict:
        data = payload.model_dump()
        model_fields, config_fields = split_validator_payload(data)

        obj = ValidatorConfig(
            organization_id=organization_id,
            project_id=project_id,
            config=config_fields,
            **model_fields,
        )

        session.add(obj)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400,
                "Validator already exists for this type and stage",
            )

        session.refresh(obj)
        return self.flatten(obj)

    def list(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        stage: Optional[Stage] = None,
        type: Optional[ValidatorType] = None,
    ) -> list[dict]:
        query = select(ValidatorConfig).where(
            ValidatorConfig.organization_id == organization_id,
            ValidatorConfig.project_id == project_id,
        )

        if stage:
            query = query.where(ValidatorConfig.stage == stage)

        if type:
            query = query.where(ValidatorConfig.type == type)

        rows = session.exec(query).all()
        return [self.flatten(r) for r in rows]

    def get(
        self,
        session: Session,
        id: UUID,
        organization_id: int,
        project_id: int,
    ) -> ValidatorConfig:
        obj = session.get(ValidatorConfig, id)

        if (
            not obj
            or obj.organization_id != organization_id
            or obj.project_id != project_id
        ):
            raise HTTPException(404, "Validator not found")

        return obj

    def update(self, session: Session, obj: ValidatorConfig, update_data: dict) -> dict:
        model_fields, config_fields = split_validator_payload(update_data)

        for k, v in model_fields.items():
            setattr(obj, k, v)

        if config_fields:
            obj.config = {**(obj.config or {}), **config_fields}

        obj.updated_at = now()
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400,
                "Validator already exists for this type and stage",
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(obj)
        return self.flatten(obj)

    def delete(self, session: Session, obj: ValidatorConfig):
        session.delete(obj)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

    def flatten(self, row: ValidatorConfig) -> dict:
        base = row.model_dump(exclude={"config"})
        return {**base, **(row.config or {})}


validator_config_crud = ValidatorConfigCrud()
