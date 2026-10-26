"""A catalog dependency from a view to a referenced object."""

from pydantic import BaseModel


class ViewDependencyMetadata(BaseModel):
    """A catalog dependency from a view to a referenced object."""

    schema_name: str
    view_name: str
    view_type: str
    referenced_schema_name: str | None = None
    referenced_object_name: str
    referenced_object_type: str
    dependency_type: str
