"""Trigger definition, execution events, target and status."""

from pydantic import BaseModel


class TriggerMetadata(BaseModel):
    """Trigger definition, execution events, target and status."""

    schema_name: str
    name: str
    trigger_type: str
    triggering_event: str
    base_object_type: str | None = None
    table_owner: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    referencing_names: str | None = None
    when_clause: str | None = None
    status: str | None = None
    description: str | None = None
    action_type: str | None = None
    trigger_body: str | None = None
