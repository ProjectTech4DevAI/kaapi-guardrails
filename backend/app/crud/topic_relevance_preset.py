from sqlmodel import Session, select
from uuid import UUID
from datetime import datetime

from app.models.config.topic_relevance_preset import TopicRelevancePreset
from app.schemas.topic_relevance_preset import (
    TopicRelevancePresetCreate,
    TopicRelevancePresetUpdate,
)


class TopicRelevancePresetCrud:
    def create(
        self,
        session: Session,
        payload: TopicRelevancePresetCreate,
        organization_id: int,
        project_id: int,
    ):
        obj = TopicRelevancePreset(
            **payload.model_dump(),
            organization_id=organization_id,
            project_id=project_id,
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    def list(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        offset: int = 0,
        limit: int | None = None,
    ):
        stmt = (
            select(TopicRelevancePreset)
            .where(
                TopicRelevancePreset.organization_id == organization_id,
                TopicRelevancePreset.project_id == project_id,
            )
            .offset(offset)
        )

        if limit:
            stmt = stmt.limit(limit)

        return session.exec(stmt).all()

    def get(self, session: Session, id: UUID, organization_id: int, project_id: int):
        stmt = select(TopicRelevancePreset).where(
            TopicRelevancePreset.id == id,
            TopicRelevancePreset.organization_id == organization_id,
            TopicRelevancePreset.project_id == project_id,
        )
        obj = session.exec(stmt).first()
        if not obj:
            raise ValueError("Topic relevance preset not found")
        return obj

    def update(
        self,
        session: Session,
        id: UUID,
        organization_id: int,
        project_id: int,
        payload: TopicRelevancePresetUpdate,
    ):
        obj = self.get(session, id, organization_id, project_id)

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(obj, key, value)

        obj.updated_at = datetime.utcnow()
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    def delete(self, session: Session, obj: TopicRelevancePreset):
        session.delete(obj)
        session.commit()


topic_relevance_preset_crud = TopicRelevancePresetCrud()
