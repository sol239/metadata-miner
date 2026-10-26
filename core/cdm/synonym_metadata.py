"""A declared object alias; synonym chains are not resolved."""

from pydantic import BaseModel


class SynonymMetadata(BaseModel):
    """A declared object alias; synonym chains are not resolved."""

    schema_name: str
    name: str
    table_owner: str | None = None
    table_name: str | None = None
    db_link: str | None = None
