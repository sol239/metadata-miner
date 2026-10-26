"""A catalog object or subobject."""

from datetime import datetime

from pydantic import BaseModel


class ObjectMetadata(BaseModel):
    """A catalog object or subobject."""

    schema_name: str
    name: str
    object_type: str
    subobject_name: str | None = None
    object_id: int | None = None
    status: str | None = None
    created: datetime | None = None
    last_ddl_time: datetime | None = None
    temporary: bool | None = None
    generated: bool | None = None
