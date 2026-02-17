from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.config.ban_list import BanList
from app.schemas.ban_list import BanListCreate, BanListUpdate
from app.utils import now


class BanListCrud:
    def create(
        self,
        session: Session,
        data: BanListCreate,
        organization_id: int,
        project_id: int,
    ) -> BanList:
        ban_list = BanList(
            **data.model_dump(),
            organization_id=organization_id,
            project_id=project_id,
        )
        session.add(ban_list)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400, "Ban list already exists for the given configuration"
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(ban_list)
        return ban_list

    def get(
        self,
        session: Session,
        id: UUID,
        organization_id: int,
        project_id: int,
        require_owner: bool = False,
    ) -> BanList:
        ban_list = session.get(BanList, id)

        if ban_list is None:
            raise HTTPException(status_code=404, detail="Ban list not found")

        if require_owner or not ban_list.is_public:
            self.check_owner(ban_list, organization_id, project_id)

        return ban_list

    def list(
        self,
        session: Session,
        organization_id: int,
        project_id: int,
        domain: Optional[str] = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> List[BanList]:
        query = select(BanList).where(
            (
                (BanList.organization_id == organization_id)
                & (BanList.project_id == project_id)
            )
            | (BanList.is_public == True)
        )

        if domain:
            query = query.where(BanList.domain == domain)

        query = query.order_by(BanList.created_at.desc(), BanList.id.desc())

        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(session.exec(query))

    def update(
        self,
        session: Session,
        id: UUID,
        organization_id: int,
        project_id: int,
        data: BanListUpdate,
    ) -> BanList:
        ban_list = self.get(
            session,
            id,
            organization_id,
            project_id,
            require_owner=True,
        )
        update_data = data.model_dump(exclude_unset=True)

        for field_name, field_value in update_data.items():
            setattr(ban_list, field_name, field_value)

        ban_list.updated_at = now()

        session.add(ban_list)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                400, "Ban list already exists for the given configuration"
            )
        except Exception:
            session.rollback()
            raise

        session.refresh(ban_list)
        return ban_list

    def delete(self, session: Session, ban_list: BanList):
        session.delete(ban_list)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

    def check_owner(
        self, ban_list: BanList, organization_id: int, project_id: int
    ) -> None:
        is_owner = (
            ban_list.organization_id == organization_id
            and ban_list.project_id == project_id
        )

        if not is_owner:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource.",
            )


ban_list_crud = BanListCrud()
