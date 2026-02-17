import logging
import functools as ft
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Dict, Generic, Optional, TypeVar

from app.core.constants import VALIDATOR_CONFIG_SYSTEM_FIELDS as SYSTEM_FIELDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar("T")


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def split_validator_payload(data: dict):
    model_fields = {}
    config_fields = {}

    for key, value in data.items():
        if key in SYSTEM_FIELDS:
            model_fields[key] = value
        else:
            config_fields[key] = value

    overlap = set(model_fields) & set(config_fields)
    if overlap:
        raise ValueError(f"Config keys conflict with reserved field names: {overlap}")

    return model_fields, config_fields


@ft.singledispatch
def load_description(filename: Path) -> str:
    if not filename.exists():
        this = Path(__file__)
        filename = this.parent.joinpath("api", "docs", filename)

    return filename.read_text()


@load_description.register
def _(filename: str) -> str:
    return load_description(Path(filename))


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def success_response(
        cls, data: T, metadata: Optional[Dict[str, Any]] = None
    ) -> "APIResponse[T]":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def failure_response(
        cls,
        error: str | list,
        data: Optional[T] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "APIResponse[T]":
        if isinstance(error, list):  # to handle cases when error is a list of errors
            error_message = "\n".join(
                [
                    f"{err.get('loc', 'unknown')}: {err.get('msg', str(err))}"
                    for err in error
                ]
            )
        else:
            error_message = error

        return cls(success=False, data=data, error=error_message, metadata=metadata)
