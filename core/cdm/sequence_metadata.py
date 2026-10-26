"""Sequence configuration; last_number is persisted, not necessarily current."""

from pydantic import BaseModel


class SequenceMetadata(BaseModel):
    """Sequence configuration; last_number is persisted, not necessarily current."""

    schema_name: str
    name: str
    min_value: int
    max_value: int
    increment_by: int
    cycle_flag: bool
    order_flag: bool
    cache_size: int
    last_number: int
