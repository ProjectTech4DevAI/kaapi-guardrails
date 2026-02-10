from uuid import UUID
from datetime import datetime
from typing import List, Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel

class BanListBase(SQLModel):
    model_config = ConfigDict(extra="allow")

    name: str
    description: str
    banned_words: list[str]
    domain: str
    is_public: bool = False


class BanListCreate(BanListBase):
    pass


class BanListUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    banned_words: Optional[list[str]] = None
    domain: Optional[str] = None
    is_public: Optional[bool] = None


class BanListResponse(BanListBase):
    id: UUID