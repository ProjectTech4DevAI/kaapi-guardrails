from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models.config.ban_list_table import BanList
from app.schemas.ban_list_config import BanListCreate, BanListUpdate
from app.utils import now

class BanListCrud:

    def create(     
        self,
        db: Session,
        *,
        data: BanListCreate,
        org_id: int,
        project_id: int,
    ) -> BanList:
        obj = BanList(
            **data.model_dump(),
            org_id=org_id,
            project_id=project_id,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get(self, db: Session, id: UUID) -> Optional[BanList]:
        return db.get(BanList, id)

    def list(
        self,
        db: Session,
        *,
        org_id: int,
        project_id: int,
        domain: Optional[str] = None,
    ) -> List[BanList]:
        stmt = select(BanList).where(
            (
                (BanList.org_id == org_id) &
                (BanList.project_id == project_id)
            ) |
            (BanList.is_public == True)
        )

        if domain:
            stmt = stmt.where(BanList.domain == domain)

        return list(db.exec(stmt))

    def update(
        self,
        db: Session,
        *,
        obj: BanList,
        data: BanListUpdate,
    ) -> BanList:
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(obj, k, v)

        obj.updated_at = now()

        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, obj: BanList):
        db.delete(obj)
        db.commit()


ban_list_crud = BanListCrud()
