"""Oracle metadata mappings using the OpenMetadata generated SDK models."""

from collections import defaultdict
import re
from uuid import UUID

from metadata.generated.schema.api.data.createDatabaseSchema import (  # pyright: ignore[reportMissingTypeStubs]
    CreateDatabaseSchemaRequest,
)
from metadata.generated.schema.api.data.createTable import (  # pyright: ignore[reportMissingTypeStubs]
    CreateTableRequest,
)
from metadata.generated.schema.api.lineage.addLineage import (  # pyright: ignore[reportMissingTypeStubs]
    AddLineageRequest,
)
from metadata.generated.schema.entity.data.table import (  # pyright: ignore[reportMissingTypeStubs]
    Column,
    ColumnProfile,
    Constraint,
    ConstraintType,
    DataType,
    TableConstraint,
    TableProfile,
    TableType,
)
from metadata.generated.schema.type.basic import (  # pyright: ignore[reportMissingTypeStubs]
    FullyQualifiedEntityName,
)

from core.cdm import (
    ColumnMetadata,
    ColumnStatisticsMetadata,
    ConstraintMetadata,
    SynonymMetadata,
    TableMetadata,
    TableStatisticsMetadata,
    UserMetadata,
    ViewDependencyMetadata,
    ViewMetadata,
)

from .IOpenMetadataMapper import IOpenMetadataMapper


class OracleMapper(IOpenMetadataMapper):
    """Convert extracted Oracle metadata into validated OpenMetadata payloads.

    Args:
        database_fqn: Existing OpenMetadata database FQN, e.g. ``oracle.library``.
            The server assigns entity IDs; mapping produces creation requests.
    """

    def __init__(self, database_fqn: str) -> None:
        if not database_fqn.strip():
            raise ValueError("database_fqn must not be empty")
        self.database_fqn = database_fqn

    def _fqn(self, *names: str) -> str:
        parts = [f'"{name}"' if "." in name else name for name in names]
        if any('"' in name for name in names):
            raise ValueError(
                "Names containing double quotes require explicit FQN resolution"
            )
        return ".".join([self.database_fqn, *parts])

    def map_column(self, column: ColumnMetadata) -> Column:
        type_mapping = {
            "VARCHAR2": DataType.VARCHAR,
            "NVARCHAR2": DataType.VARCHAR,
            "VARCHAR": DataType.VARCHAR,
            "CHAR": DataType.CHAR,
            "NCHAR": DataType.CHAR,
            "NUMBER": DataType.NUMERIC,
            "DECIMAL": DataType.DECIMAL,
            "NUMERIC": DataType.NUMERIC,
            "INTEGER": DataType.INT,
            "FLOAT": DataType.FLOAT,
            "BINARY_FLOAT": DataType.FLOAT,
            "BINARY_DOUBLE": DataType.DOUBLE,
            "DATE": DataType.DATE,
            "CLOB": DataType.CLOB,
            "NCLOB": DataType.CLOB,
            "BLOB": DataType.BLOB,
            "RAW": DataType.VARBINARY,
            "LONG RAW": DataType.BINARY,
            "LONG": DataType.LONG,
            "ROWID": DataType.ROWID,
            "UROWID": DataType.ROWID,
            "XMLTYPE": DataType.XML,
            "JSON": DataType.JSON,
            "BOOLEAN": DataType.BOOLEAN,
        }
        oracle_type = column.data_type.upper().strip()
        base_type = re.sub(r"\([^)]*\)", "", oracle_type).strip()
        if base_type.startswith("TIMESTAMP"):
            data_type = (
                DataType.TIMESTAMPZ if "TIME ZONE" in base_type else DataType.TIMESTAMP
            )
        elif base_type.startswith("INTERVAL"):
            data_type = DataType.INTERVAL
        else:
            data_type = type_mapping.get(base_type, DataType.UNKNOWN)
        length = None
        if data_type in {
            DataType.VARCHAR,
            DataType.CHAR,
            DataType.BINARY,
            DataType.VARBINARY,
        }:
            length = (
                column.char_length if column.char_used == "C" else column.data_length
            )
        return Column.model_validate(
            {
                "name": column.name,
                "dataType": data_type,
                "dataTypeDisplay": column.data_type,
                "description": column.description,
                "dataLength": length,
                "precision": column.data_precision,
                "scale": column.data_scale,
                "ordinalPosition": column.position,
                "constraint": (
                    Constraint.NULL if column.nullable else Constraint.NOT_NULL
                ),
            }
        )

    def map_schema(self, schema: UserMetadata) -> CreateDatabaseSchemaRequest:
        return CreateDatabaseSchemaRequest.model_validate(
            {
                "name": schema.schema_name,
                "database": self.database_fqn,
            }
        )

    def map_constraint(self, rows: list[ConstraintMetadata]) -> TableConstraint | None:
        if not rows:
            raise ValueError("A constraint must contain at least one row")
        first = rows[0]
        key = (first.schema_name, first.table_name, first.name, first.constraint_type)
        if any(
            (row.schema_name, row.table_name, row.name, row.constraint_type) != key
            for row in rows
        ):
            raise ValueError("Rows must belong to the same constraint")
        if first.constraint_type == "C":
            return None
        types = {
            "P": ConstraintType.PRIMARY_KEY,
            "U": ConstraintType.UNIQUE,
            "R": ConstraintType.FOREIGN_KEY,
        }
        if first.constraint_type not in types:
            raise ValueError(f"Unsupported constraint type: {first.constraint_type}")
        if any(row.column_name is None or row.position is None for row in rows):
            raise ValueError("Key constraints require column names and positions")
        positions = [row.position for row in rows]
        if set(positions) != set(range(1, len(rows) + 1)):
            raise ValueError("Constraint positions must be consecutive and unique")
        ordered = sorted(rows, key=lambda row: row.position or 0)
        referred: list[str] | None = None
        if first.constraint_type == "R":
            referred = []
            for row in ordered:
                if (
                    not row.referenced_schema_name
                    or not row.referenced_table_name
                    or not row.referenced_column_name
                ):
                    raise ValueError(
                        "Foreign keys require complete referenced column metadata"
                    )
                referred.append(
                    self._fqn(
                        row.referenced_schema_name,
                        row.referenced_table_name,
                        row.referenced_column_name,
                    )
                )
        return TableConstraint.model_validate(
            {
                "constraintType": types[first.constraint_type],
                "columns": [row.column_name for row in ordered],
                "referredColumns": referred,
            }
        )

    def map_table(self, table: TableMetadata) -> CreateTableRequest:
        groups: dict[tuple[str, str, str], list[ConstraintMetadata]] = defaultdict(list)
        for row in table.constraints:
            if (row.schema_name, row.table_name) != (table.schema_name, table.name):
                raise ValueError("Constraint belongs to another table")
            groups[row.schema_name, row.table_name, row.name].append(row)
        constraints = [
            mapped
            for rows in groups.values()
            if (mapped := self.map_constraint(rows)) is not None
        ]
        if any(
            (column.schema_name, column.table_name) != (table.schema_name, table.name)
            for column in table.columns
        ):
            raise ValueError("Column belongs to another table")
        columns = [
            self.map_column(column)
            for column in sorted(table.columns, key=lambda col: col.position)
        ]
        return CreateTableRequest.model_validate(
            {
                "name": table.name,
                "description": table.description,
                "databaseSchema": self._fqn(table.schema_name),
                "tableType": (
                    TableType.Partitioned if table.partitioned else TableType.Regular
                ),
                "columns": columns,
                "tableConstraints": constraints or None,
            }
        )

    def map_view(self, view: ViewMetadata) -> CreateTableRequest:
        if any(
            (column.schema_name, column.table_name) != (view.schema_name, view.name)
            for column in view.columns
        ):
            raise ValueError("Column belongs to another view")
        return CreateTableRequest.model_validate(
            {
                "name": view.name,
                "databaseSchema": self._fqn(view.schema_name),
                "tableType": TableType.View,
                "schemaDefinition": view.definition,
                "columns": [
                    self.map_column(column)
                    for column in sorted(view.columns, key=lambda col: col.position)
                ],
            }
        )

    def map_table_statistics(
        self, stats: TableStatisticsMetadata, timestamp: int
    ) -> TableProfile:
        if stats.object_type != "TABLE":
            raise ValueError(
                "Partition statistics cannot be mapped to a whole-table profile"
            )
        return TableProfile.model_validate(
            {"timestamp": timestamp, "rowCount": stats.num_rows}
        )

    def map_column_statistics(
        self, stats: ColumnStatisticsMetadata, timestamp: int
    ) -> ColumnProfile:
        return ColumnProfile.model_validate(
            {
                "name": stats.column_name,
                "timestamp": timestamp,
                "nullCount": stats.num_nulls,
                "distinctCount": stats.num_distinct,
            }
        )

    def map_view_dependency(
        self, dependency: ViewDependencyMetadata, source_id: UUID, view_id: UUID
    ) -> AddLineageRequest:
        if dependency.referenced_object_type not in {
            "TABLE",
            "VIEW",
            "MATERIALIZED VIEW",
        }:
            raise ValueError("Only table/view dependencies can map to table lineage")
        if not dependency.referenced_schema_name:
            raise ValueError("Lineage requires the referenced schema")
        return AddLineageRequest.model_validate(
            {
                "edge": {
                    "fromEntity": {
                        "id": str(source_id),
                        "type": "table",
                        "fullyQualifiedName": self._fqn(
                            dependency.referenced_schema_name,
                            dependency.referenced_object_name,
                        ),
                    },
                    "toEntity": {
                        "id": str(view_id),
                        "type": "table",
                        "fullyQualifiedName": self._fqn(
                            dependency.schema_name, dependency.view_name
                        ),
                    },
                    "lineageDetails": {"source": "ViewLineage"},
                }
            }
        )

    def map_synonym(self, synonym: SynonymMetadata) -> FullyQualifiedEntityName:
        if synonym.db_link:
            raise ValueError(
                "Remote synonyms require the target database to be resolved first"
            )
        return FullyQualifiedEntityName(self._fqn(synonym.schema_name, synonym.name))
