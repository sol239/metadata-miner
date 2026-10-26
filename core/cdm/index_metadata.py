"""One indexed column; composite indexes occupy multiple records."""

from pydantic import BaseModel


class IndexMetadata(BaseModel):
    """One indexed column; composite indexes occupy multiple records."""

    name: str
    index_type: str
    owner: str
    table_owner: str
    table_name: str
    uniqueness: str
    column_name: str | None = None
    position: int | None = None
    sort_order: str | None = None
    description: str | None = None
