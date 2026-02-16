from uuid import UUID
from typing import Annotated, Optional

from pydantic import StringConstraints
from sqlmodel import Field
from sqlmodel import SQLModel

MAX_BANNED_WORD_LENGTH = 100
MAX_BANNED_WORDS_ITEMS = 1000

BannedWord = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=MAX_BANNED_WORD_LENGTH
    ),
]
BannedWords = Annotated[list[BannedWord], Field(max_length=MAX_BANNED_WORDS_ITEMS)]


class BanListBase(SQLModel):
    name: str
    description: str
    banned_words: BannedWords
    domain: str
    is_public: bool = False


class BanListCreate(BanListBase):
    pass


class BanListUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    banned_words: Optional[BannedWords] = None
    domain: Optional[str] = None
    is_public: Optional[bool] = None


class BanListResponse(BanListBase):
    id: UUID
