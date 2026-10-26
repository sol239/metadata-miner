"""Interfaces for extracting metadata from SQL database systems."""

from abc import ABC, abstractmethod

from core.cdm import (
    UserMetadata,
    ObjectMetadata,
    TableMetadata,
    ColumnMetadata,
    ViewMetadata,
    IndexMetadata,
    TriggerMetadata,
    SequenceMetadata,
    SynonymMetadata,
    TableStatisticsMetadata,
    ColumnStatisticsMetadata,
    HistogramMetadata,
    ConstraintMetadata,
    ViewDependencyMetadata,
)


class ISQLExtractor(ABC):
    """Define the metadata extraction contract for a SQL database.

    Implementations query the catalogs available in a specific database
    system and return validated Pydantic model lists. Each method extracts
    metadata for one schema and preserves catalog row granularity (for
    example, one record per column or constraint column).
    """

    @abstractmethod
    def extract_users(self, schema_name: str) -> list[UserMetadata]:
        """Extract metadata describing the requested schema.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models containing schema identity and creation metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_objects(self, schema_name: str) -> list[ObjectMetadata]:
        """Extract objects owned by the requested schema.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with object names, types, status, and timestamps.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_tables(self, schema_name: str) -> list[TableMetadata]:
        """Extract table definitions and available table descriptions.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            Table models containing properties, descriptions, columns, constraints,
            and indexes, matched by schema and table name.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_columns(self, schema_name: str) -> list[ColumnMetadata]:
        """Extract column definitions and available column descriptions.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with column order, data type, size, nullability,
            default value, and comments when present.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_views(self, schema_name: str) -> list[ViewMetadata]:
        """Extract view definitions owned by the requested schema.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            View models containing definitions, read-only status, columns, and
            referenced object dependencies.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_indexes(self, schema_name: str) -> list[IndexMetadata]:
        """Extract indexes on tables owned by the requested schema.

        Args:
            schema_name: Name of the table-owning schema to inspect.

        Returns:
            A list of metadata models with indexed columns, positions, sort order, uniqueness, and its
            table description when one is available.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_triggers(self, schema_name: str) -> list[TriggerMetadata]:
        """Extract triggers owned by the requested schema.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with trigger timing, events, target, status,
            conditions, and trigger body.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_sequences(self, schema_name: str) -> list[SequenceMetadata]:
        """Extract sequence configuration for the requested schema.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with sequence bounds, increment, cache, and persisted
            last-number metadata. The last number may not be the current value.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_synonyms(self, schema_name: str) -> list[SynonymMetadata]:
        """Extract synonyms owned by the requested schema.

        Args:
            schema_name: Name of the schema to inspect. Use ``PUBLIC`` to
                request public synonyms where supported by the catalog.

        Returns:
            A list of metadata models with synonym names and their declared targets,
            including database links when present.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_table_statistics(self, schema_name: str) -> list[TableStatisticsMetadata]:
        """Extract available optimizer statistics for tables in a schema.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with row counts, block counts, average row length,
            sample size, analysis time, freshness, and global-statistics status.
            Statistics may be absent or out of date.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_column_statistics(self, schema_name: str) -> list[ColumnStatisticsMetadata]:
        """Extract available optimizer statistics for table columns.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with distinct and null counts, value bounds, density,
            average column length, and sample size. Encoded bounds may require
            database-specific decoding based on the column data type.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_histograms(self, schema_name: str) -> list[HistogramMetadata]:
        """Extract histogram endpoints for columns in a schema.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with one row per histogram endpoint and its value.
            Endpoint rows alone do not establish whether a column has a
            histogram; consult the column statistics when that distinction
            matters.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_constraints(self, schema_name: str) -> list[ConstraintMetadata]:
        """Extract primary, foreign, unique, and CHECK constraints.

        Args:
            schema_name: Name of the schema to inspect.

        Returns:
            A list of metadata models with one row per constraint column, including its
            position and referenced column for foreign keys. Single-column
            constraints have one row; composite constraints have multiple.
            CHECK constraints include Oracle NOT NULL constraints and their
            search conditions where available.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_view_dependencies(self, schema_name: str) -> list[ViewDependencyMetadata]:
        """Extract catalog dependencies declared by schema views.

        Args:
            schema_name: Name of the schema whose views to inspect.

        Returns:
            A list of metadata models with each view and its referenced objects. The catalog
            reports declared dependencies; it does not resolve synonym chains.
        """
        raise NotImplementedError
