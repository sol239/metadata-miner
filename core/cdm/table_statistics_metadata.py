"""Stored optimizer estimates, including sampling and freshness."""

from datetime import datetime

from pydantic import BaseModel


class TableStatisticsMetadata(BaseModel):
    """Stored optimizer estimates, including sampling and freshness."""

    schema_name: str
    table_name: str
    object_type: str
    num_rows: int | None = None
    blocks: int | None = None
    empty_blocks: int | None = None
    avg_row_len: float | None = None
    sample_size: int | None = None
    last_analyzed: datetime | None = None
    stale_stats: bool | None = None
    global_stats: bool | None = None
