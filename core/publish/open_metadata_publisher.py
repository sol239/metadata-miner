"""Publish validated OpenMetadata SDK requests through an injected client."""

from typing import cast

from metadata.generated.schema.api.data.createDatabaseSchema import (  # pyright: ignore[reportMissingTypeStubs]
    CreateDatabaseSchemaRequest,
)
from metadata.generated.schema.api.data.createTable import CreateTableRequest  # pyright: ignore[reportMissingTypeStubs]
from metadata.generated.schema.api.data.createTableProfile import (  # pyright: ignore[reportMissingTypeStubs]
    CreateTableProfileRequest,
)
from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest  # pyright: ignore[reportMissingTypeStubs]
from metadata.generated.schema.entity.data.databaseSchema import DatabaseSchema  # pyright: ignore[reportMissingTypeStubs]
from metadata.generated.schema.entity.data.table import (  # pyright: ignore[reportMissingTypeStubs]
    ColumnProfile, Table, TableProfile,
)
from metadata.ingestion.ometa.ometa_api import OpenMetadata  # pyright: ignore[reportMissingTypeStubs]


class OpenMetadataPublisher:
    """Publish schemas, tables/views, profiles and lineage to OpenMetadata.

    The caller configures and closes the injected client. Columns, constraints,
    and aliases are published as part of their table creation request.
    SDK and server errors propagate to the caller.
    """

    def __init__(
        self,
        client: OpenMetadata[
            Table | DatabaseSchema, CreateTableRequest | CreateDatabaseSchemaRequest
        ],
    ) -> None:
        self.client = client

    def publish_schema(self, request: CreateDatabaseSchemaRequest) -> DatabaseSchema:
        return cast(DatabaseSchema, self.client.create_or_update(request))

    def publish_table(self, request: CreateTableRequest) -> Table:
        return cast(Table, self.client.create_or_update(request))

    def publish_view(self, request: CreateTableRequest) -> Table:
        return self.publish_table(request)

    def publish_profile(self, table: Table, request: CreateTableProfileRequest) -> Table:
        return self.client.ingest_profile_data(table, request)

    def publish_table_statistics(
        self, table: Table, profile: TableProfile,
        column_profiles: list[ColumnProfile] | None = None,
    ) -> Table:
        request = CreateTableProfileRequest(
            tableProfile=profile, columnProfile=column_profiles,
        )
        return self.publish_profile(table, request)

    def publish_lineage(self, request: AddLineageRequest) -> dict[str, object]:
        return self.client.add_lineage(request)
