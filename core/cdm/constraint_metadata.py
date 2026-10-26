"""One constraint column, including CHECK/NOT NULL and referenced keys."""

from pydantic import BaseModel


class ConstraintMetadata(BaseModel):
    """One constraint column, including CHECK/NOT NULL and referenced keys."""

    schema_name: str
    table_name: str
    name: str
    constraint_type: str
    search_condition_vc: str | None = None
    column_name: str | None = None
    position: int | None = None
    referenced_schema_name: str | None = None
    referenced_table_name: str | None = None
    referenced_column_name: str | None = None
    delete_rule: str | None = None
    status: str | None = None
    deferrable: str | None = None
    deferred: str | None = None
    validated: str | None = None
