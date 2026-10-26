"""One histogram endpoint; interpretation depends on histogram type."""

from pydantic import BaseModel


class HistogramMetadata(BaseModel):
    """One histogram endpoint; interpretation depends on histogram type."""

    schema_name: str
    table_name: str
    column_name: str
    endpoint_number: int
    endpoint_value: float | None = None
    endpoint_actual_value: str | None = None
    endpoint_actual_value_raw: bytes | None = None
    endpoint_repeat_count: int | None = None
