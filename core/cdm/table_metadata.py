"""Table properties and its database description."""

from pydantic import BaseModel, Field

from .column_metadata import ColumnMetadata
from .constraint_metadata import ConstraintMetadata
from .index_metadata import IndexMetadata


class TableMetadata(BaseModel):
    """Table properties and its database description."""

    schema_name: str
    name: str
    tablespace_name: str | None = None
    status: str | None = None
    temporary: bool | None = None
    partitioned: bool | None = None
    iot_type: str | None = None
    nested: bool | None = None
    description: str | None = None

    columns: list[ColumnMetadata] = Field(default_factory=list[ColumnMetadata])
    constraints: list[ConstraintMetadata] = Field(default_factory=list[ConstraintMetadata])
    indexes: list[IndexMetadata] = Field(default_factory=list[IndexMetadata])
