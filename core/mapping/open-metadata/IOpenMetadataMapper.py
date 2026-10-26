"""Contracts for converting extracted metadata into OpenMetadata SDK models."""

from abc import ABC, abstractmethod
from uuid import UUID

from metadata.generated.schema.api.data.createDatabaseSchema import CreateDatabaseSchemaRequest  # pyright: ignore[reportMissingTypeStubs]
from metadata.generated.schema.api.data.createTable import CreateTableRequest  # pyright: ignore[reportMissingTypeStubs]
from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest  # pyright: ignore[reportMissingTypeStubs]
from metadata.generated.schema.entity.data.table import Column, ColumnProfile, TableConstraint, TableProfile  # pyright: ignore[reportMissingTypeStubs]
from metadata.generated.schema.type.basic import FullyQualifiedEntityName  # pyright: ignore[reportMissingTypeStubs]

from core.cdm import (
    ColumnMetadata, ColumnStatisticsMetadata, ConstraintMetadata, SynonymMetadata,
    TableMetadata, TableStatisticsMetadata, UserMetadata, ViewDependencyMetadata, ViewMetadata,
)


class IOpenMetadataMapper(ABC):
    """Map common metadata to SDK payloads without calling an OpenMetadata server.

    Indexes, triggers, sequences and raw histogram endpoints have no direct
    equivalent in the table creation API. CHECK conditions are not supported
    by TableConstraint; NOT NULL is represented by Column.constraint.
    """

    @abstractmethod
    def map_column(self, column: ColumnMetadata) -> Column:
        """Map one column, including nullability and type details."""
        raise NotImplementedError

    @abstractmethod
    def map_schema(self, schema: UserMetadata) -> CreateDatabaseSchemaRequest:
        """Map an Oracle schema, rather than an application user account."""
        raise NotImplementedError

    @abstractmethod
    def map_table(self, table: TableMetadata) -> CreateTableRequest:
        """Map an assembled table and its supported key constraints."""
        raise NotImplementedError

    @abstractmethod
    def map_view(self, view: ViewMetadata) -> CreateTableRequest:
        """Map a view as a table with TableType.View and its SQL definition."""
        raise NotImplementedError

    @abstractmethod
    def map_constraint(self, rows: list[ConstraintMetadata]) -> TableConstraint | None:
        """Map ordered rows of one composite key; return None for CHECK rows."""
        raise NotImplementedError

    @abstractmethod
    def map_table_statistics(self, stats: TableStatisticsMetadata, timestamp: int) -> TableProfile:
        """Map table estimates with an explicit Unix timestamp in milliseconds."""
        raise NotImplementedError

    @abstractmethod
    def map_column_statistics(self, stats: ColumnStatisticsMetadata, timestamp: int) -> ColumnProfile:
        """Map counts; Oracle RAW bounds require decoding before use."""
        raise NotImplementedError

    @abstractmethod
    def map_view_dependency(
        self, dependency: ViewDependencyMetadata, source_id: UUID, view_id: UUID
    ) -> AddLineageRequest:
        """Map upstream table/view to downstream view using existing entity IDs."""
        raise NotImplementedError

    @abstractmethod
    def map_synonym(self, synonym: SynonymMetadata) -> FullyQualifiedEntityName:
        """Map a local synonym to an alias FQN for its target table."""
        raise NotImplementedError
