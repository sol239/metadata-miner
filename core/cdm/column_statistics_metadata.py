"""Stored column statistics; bounds retain Oracle RAW encoding."""

from pydantic import BaseModel


class ColumnStatisticsMetadata(BaseModel):
    """Stored column statistics; bounds retain Oracle RAW encoding."""

    schema_name: str
    table_name: str
    column_name: str
    num_distinct: int | None = None
    num_nulls: int | None = None
    low_value: bytes | None = None
    high_value: bytes | None = None
    density: float | None = None
    avg_col_len: float | None = None
    sample_size: int | None = None
