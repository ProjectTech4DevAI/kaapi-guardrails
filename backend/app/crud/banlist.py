from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.config.banlist import BanList
from app.schemas.banlist import BanListCreate, BanListUpdate
from app.utils import now

class BanListCrud:
    def create(     
        self,
        session: Session,
        data: BanListCreate,
        organization_id: int,
        project_id: int,
    ) -> BanList:
        obj = BanList(
            **data.model_dump(),
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
                "Banlist already exists for the given configuration"
            )
        
        session.refresh(obj)
        return obj

    def get(
        self, 
        session: Session, 
        id: UUID,
        organization_id: int,
        project_id: int
    ) -> BanList:
        obj = session.get(BanList, id)

        if obj is None:
            raise HTTPException(status_code=404, detail="Banlist not found")

        if not obj.is_public:
            self.check_owner(obj, organization_id, project_id)

        return obj

    def list(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        domain: Optional[str] = None,
    ) -> List[BanList]:
        stmt = select(BanList).where(
            (
                (BanList.organization_id == organization_id) &
                (BanList.project_id == project_id)
            ) |
            (BanList.is_public == True)
        )

        if domain:
            stmt = stmt.where(BanList.domain == domain)

        return list(session.exec(stmt))

    def update(
        self,
        session: Session,
        obj: BanList,
        data: BanListUpdate,
    ) -> BanList:
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(obj, k, v)

        obj.updated_at = now()

        session.add(obj)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400,
                "Banlist already exists for the given configuration"
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(obj)
        return obj

    def delete(self, session: Session, obj: BanList):
        session.delete(obj)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

    def check_owner(self, obj, organization_id, project_id):
        if obj.organization_id != organization_id or obj.project_id != project_id:
            raise HTTPException(status_code=403, detail="Not owner")

banlist_crud = BanListCrud()