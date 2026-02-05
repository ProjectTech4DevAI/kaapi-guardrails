from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.config.validator_config_table import ValidatorConfig
from app.schemas.validator_config import Stage, ValidatorType
from app.utils import split_validator_payload


class ValidatorConfigCrud:
    def create(
            self, 
            session: Session, 
            org_id: int, 
            project_id: int, 
            payload
        ):
        data = payload.model_dump()
        base, config = split_validator_payload(data)

        obj = ValidatorConfig(
            org_id=org_id,
            project_id=project_id,
            config=config,
            **base,
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
        return self._flatten(obj)

    def list(
        self,
        session: Session,
        org_id: int,
        project_id: int,
        stage: Optional[Stage] = None,
        type: Optional[ValidatorType] = None,
    ) -> List[dict]:
        query = select(ValidatorConfig).where(
            ValidatorConfig.org_id == org_id,
            ValidatorConfig.project_id == project_id,
        )

        if stage:
            query = query.where(ValidatorConfig.stage == stage)

        if type:
            query = query.where(ValidatorConfig.type == type)

        rows = session.exec(query).all()
        return [self._flatten(r) for r in rows]

    def get_or_404(
        self,
        session: Session,
        id: UUID,
        org_id: int,
        project_id: int,
    ) -> ValidatorConfig:
        obj = session.get(ValidatorConfig, id)

        if not obj or obj.org_id != org_id or obj.project_id != project_id:
            raise HTTPException(404, "Validator not found")

        return obj

    def update(
            self, 
            session: Session, 
            obj: ValidatorConfig, 
            update_data: dict
        ):
        base, config = split_validator_payload(update_data)

        for k, v in base.items():
            setattr(obj, k, v)

        if config:
            obj.config = {**(obj.config or {}), **config}

        session.commit()
        session.refresh(obj)

        return self._flatten(obj)

    def delete(self, session: Session, obj: ValidatorConfig):
        session.delete(obj)
        session.commit()

    def _flatten(self, row: ValidatorConfig) -> dict:
        base = row.model_dump(exclude={"config"})
        return {**base, **(row.config or {})}


validator_config_crud = ValidatorConfigCrud()
