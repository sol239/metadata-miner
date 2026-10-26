"""A view and its complete SQL definition."""

from pydantic import BaseModel, Field

from .column_metadata import ColumnMetadata
from .view_dependency_metadata import ViewDependencyMetadata


class ViewMetadata(BaseModel):
    """A view and its complete SQL definition."""

    schema_name: str
    name: str
    text_length: int | None = None
    definition: str | None = None
    read_only: bool | None = None

    columns: list[ColumnMetadata] = Field(default_factory=list[ColumnMetadata])
    dependencies: list[ViewDependencyMetadata] = Field(default_factory=list[ViewDependencyMetadata])
