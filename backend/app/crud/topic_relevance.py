from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.config.topic_relevance import TopicRelevance
from app.schemas.topic_relevance import (
    TopicRelevanceCreate,
    TopicRelevanceUpdate,
)
from app.utils import now


class TopicRelevanceCrud:
    def create(
        self,
        session: Session,
        payload: TopicRelevanceCreate,
        organization_id: int,
        project_id: int,
    ) -> TopicRelevance:
        topic_relevance_obj = TopicRelevance(
            **payload.model_dump(),
            organization_id=organization_id,
            project_id=project_id,
        )
        session.add(topic_relevance_obj)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400, "Topic relevance with the same configuration already exists"
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(topic_relevance_obj)
        return topic_relevance_obj

    def get(
        self, session: Session, id: UUID, organization_id: int, project_id: int
    ) -> TopicRelevance:
        query = select(TopicRelevance).where(
            TopicRelevance.id == id,
            TopicRelevance.organization_id == organization_id,
            TopicRelevance.project_id == project_id,
        )
        topic_relevance_obj = session.exec(query).first()
        if not topic_relevance_obj:
            raise HTTPException(404, "Topic relevance preset not found")
        return topic_relevance_obj

    def list(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        offset: int = 0,
        limit: int | None = None,
    ) -> List[TopicRelevance]:
        query = (
            select(TopicRelevance)
            .where(
                TopicRelevance.organization_id == organization_id,
                TopicRelevance.project_id == project_id,
            )
            .order_by(TopicRelevance.created_at, TopicRelevance.id)
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
        payload: TopicRelevanceUpdate,
    ) -> TopicRelevance:
        topic_relevance_obj = self.get(session, id, organization_id, project_id)

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(topic_relevance_obj, key, value)

        topic_relevance_obj.updated_at = now()
        session.add(topic_relevance_obj)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400, "Topic relevance with the same configuration already exists"
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(topic_relevance_obj)
        return topic_relevance_obj

    def delete(self, session: Session, topic_relevance_obj: TopicRelevance):
        session.delete(topic_relevance_obj)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise


topic_relevance_crud = TopicRelevanceCrud()
