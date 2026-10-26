"""AAA publisher tests with a mocked SDK client; no server writes."""

from unittest.mock import Mock
from uuid import UUID

import pytest
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

from core.publish import OpenMetadataPublisher


def table_entity() -> Table:
    return Table.model_validate({"id": str(UUID(int=1)), "name": "BOOKS", "columns": []})


def test_publish_schema() -> None:
    # Arrange
    request = CreateDatabaseSchemaRequest.model_validate({"name": "LIB", "database": "oracle.library"})
    expected = DatabaseSchema.model_validate({
        "id": str(UUID(int=2)), "name": "LIB",
        "service": {"id": str(UUID(int=3)), "type": "databaseService"},
        "database": {"id": str(UUID(int=4)), "type": "database"},
    })
    client = Mock(spec=OpenMetadata)
    client.create_or_update.return_value = expected
    # Act
    actual = OpenMetadataPublisher(client).publish_schema(request)
    # Assert
    assert actual is expected
    client.create_or_update.assert_called_once_with(request)


@pytest.mark.parametrize("is_view", [False, True])
def test_publish_table_or_view(is_view: bool) -> None:
    # Arrange
    request = CreateTableRequest.model_validate({"name": "BOOKS", "columns": [],
        "databaseSchema": "oracle.library.LIB", "tableType": "View" if is_view else "Regular"})
    expected = table_entity()
    client = Mock(spec=OpenMetadata)
    client.create_or_update.return_value = expected
    publisher = OpenMetadataPublisher(client)
    # Act
    actual = publisher.publish_view(request) if is_view else publisher.publish_table(request)
    # Assert
    assert actual is expected
    client.create_or_update.assert_called_once_with(request)


def test_publish_profile() -> None:
    # Arrange
    table = table_entity()
    request = CreateTableProfileRequest.model_validate({"tableProfile": {"timestamp": 1700000000000, "rowCount": 10}})
    client = Mock(spec=OpenMetadata)
    client.ingest_profile_data.return_value = table
    # Act
    actual = OpenMetadataPublisher(client).publish_profile(table, request)
    # Assert
    assert actual is table
    client.ingest_profile_data.assert_called_once_with(table, request)


def test_publish_table_statistics_includes_column_profiles() -> None:
    # Arrange
    table = table_entity()
    profile = TableProfile.model_validate({"timestamp": 1700000000000, "rowCount": 10})
    columns = [ColumnProfile.model_validate({"name": "ID", "timestamp": 1700000000000, "nullCount": 0})]
    expected = CreateTableProfileRequest(tableProfile=profile, columnProfile=columns)
    client = Mock(spec=OpenMetadata)
    client.ingest_profile_data.return_value = table
    # Act
    actual = OpenMetadataPublisher(client).publish_table_statistics(table, profile, columns)
    # Assert
    assert actual is table
    client.ingest_profile_data.assert_called_once_with(table, expected)


def test_publish_lineage() -> None:
    # Arrange
    request = AddLineageRequest.model_validate({"edge": {
        "fromEntity": {"id": str(UUID(int=1)), "type": "table"},
        "toEntity": {"id": str(UUID(int=2)), "type": "table"},
    }})
    expected = {"status": "ok"}
    client = Mock(spec=OpenMetadata)
    client.add_lineage.return_value = expected
    # Act
    actual = OpenMetadataPublisher(client).publish_lineage(request)
    # Assert
    assert actual == expected
    client.add_lineage.assert_called_once_with(request)


def test_publish_propagates_server_errors() -> None:
    # Arrange
    request = CreateTableRequest.model_validate({"name": "BOOKS", "columns": [], "databaseSchema": "oracle.library.LIB"})
    client = Mock(spec=OpenMetadata)
    client.create_or_update.side_effect = RuntimeError("Server unavailable")
    # Act / Assert
    with pytest.raises(RuntimeError, match="Server unavailable"):
        OpenMetadataPublisher(client).publish_table(request)
