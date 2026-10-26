"""Schema identity and creation metadata."""

from datetime import datetime

from pydantic import BaseModel


class UserMetadata(BaseModel):
    """Schema identity and creation metadata."""

    schema_name: str
    user_id: int
    created: datetime
