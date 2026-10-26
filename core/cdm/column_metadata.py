"""One table or view column, including type and description."""

from pydantic import BaseModel


class ColumnMetadata(BaseModel):
    """One table or view column, including type and description."""

    schema_name: str
    table_name: str
    name: str
    data_type: str
    nullable: bool
    position: int
    description: str | None = None
    data_type_owner: str | None = None
    data_length: int | None = None
    data_precision: int | None = None
    data_scale: int | None = None
    char_length: int | None = None
    char_used: str | None = None
    default_value: str | None = None
