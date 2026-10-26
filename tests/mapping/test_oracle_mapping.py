"""AAA tests of Oracle mapping into real OpenMetadata SDK payloads."""

from datetime import datetime
from uuid import UUID

import pytest
from metadata.generated.schema.entity.data.table import (  # pyright: ignore[reportMissingTypeStubs]
    Constraint, ConstraintType, DataType, TableType,
)

from core.cdm import (
    ColumnMetadata, ColumnStatisticsMetadata, ConstraintMetadata, SynonymMetadata,
    TableMetadata, TableStatisticsMetadata, UserMetadata, ViewDependencyMetadata, ViewMetadata,
)
from core.mapping.open_metadata import IOpenMetadataMapper, OracleMapper


@pytest.fixture
def mapper() -> OracleMapper:
    return OracleMapper("oracle.library")


def column(data_type: str = "NUMBER") -> ColumnMetadata:
    return ColumnMetadata(schema_name="LIB", table_name="BOOKS", name="ID",
                          data_type=data_type, nullable=False, position=1)


@pytest.mark.parametrize(("oracle_type", "expected"), [
    ("VARCHAR2", DataType.VARCHAR), ("NUMBER", DataType.NUMERIC),
    ("DATE", DataType.DATE), ("CLOB", DataType.CLOB),
    ("TIMESTAMP(6)", DataType.TIMESTAMP),
    ("TIMESTAMP(6) WITH TIME ZONE", DataType.TIMESTAMPZ),
    ("INTERVAL DAY(2) TO SECOND(6)", DataType.INTERVAL),
    ("CUSTOM_OBJECT", DataType.UNKNOWN),
])
def test_map_column_types(mapper: OracleMapper, oracle_type: str, expected: DataType) -> None:
    # Arrange
    source = column(oracle_type)
    # Act
    actual = mapper.map_column(source)
    # Assert
    assert actual.dataType == expected
    assert actual.name.root == "ID"
    assert actual.constraint == Constraint.NOT_NULL
    assert actual.ordinalPosition == 1


def test_map_column_length_and_description(mapper: OracleMapper) -> None:
    # Arrange
    source = column("VARCHAR2").model_copy(update={
        "nullable": True, "description": "Book title", "char_used": "C",
        "char_length": 20, "data_length": 80,
    })
    # Act
    actual = mapper.map_column(source)
    # Assert
    assert actual.dataLength == 20
    assert actual.description is not None and actual.description.root == "Book title"
    assert actual.constraint == Constraint.NULL


def test_map_schema(mapper: OracleMapper) -> None:
    # Arrange
    source = UserMetadata(schema_name="LIB", user_id=42, created=datetime(2026, 1, 1))
    # Act
    actual = mapper.map_schema(source)
    # Assert
    assert isinstance(mapper, IOpenMetadataMapper)
    assert actual.name.root == "LIB"
    assert actual.database.root == "oracle.library"


def test_map_table_with_primary_key(mapper: OracleMapper) -> None:
    # Arrange
    source = TableMetadata(name="BOOKS", schema_name="LIB", description="Books",
        columns=[column()], constraints=[ConstraintMetadata(
            schema_name="LIB", table_name="BOOKS", name="PK_BOOKS",
            constraint_type="P", column_name="ID", position=1)])
    # Act
    actual = mapper.map_table(source)
    # Assert
    assert actual.tableType == TableType.Regular
    assert actual.databaseSchema.root == "oracle.library.LIB"
    assert actual.columns[0].constraint == Constraint.NOT_NULL
    assert actual.tableConstraints is not None
    assert actual.tableConstraints[0].constraintType == ConstraintType.PRIMARY_KEY
    assert actual.tableConstraints[0].columns == ["ID"]


def test_map_composite_foreign_key_in_column_order(mapper: OracleMapper) -> None:
    # Arrange
    rows = [ConstraintMetadata(schema_name="LIB", table_name="BOOKS", name="FK",
        constraint_type="R", column_name=local, position=position,
        referenced_schema_name="LIB", referenced_table_name="PARENT", referenced_column_name=remote)
        for local, position, remote in [("B", 2, "Y"), ("A", 1, "X")]]
    # Act
    actual = mapper.map_constraint(rows)
    # Assert
    assert actual is not None
    assert actual.columns == ["A", "B"]
    assert actual.referredColumns is not None
    assert [value.root for value in actual.referredColumns] == [
        "oracle.library.LIB.PARENT.X", "oracle.library.LIB.PARENT.Y"]


def test_check_constraint_has_no_table_constraint_equivalent(mapper: OracleMapper) -> None:
    # Arrange
    source = ConstraintMetadata(schema_name="LIB", table_name="BOOKS", name="CK",
                                constraint_type="C", search_condition_vc="ID > 0")
    # Act
    actual = mapper.map_constraint([source])
    # Assert
    assert actual is None


def test_mixed_constraint_rows_are_rejected(mapper: OracleMapper) -> None:
    # Arrange
    source = ConstraintMetadata(schema_name="LIB", table_name="BOOKS", name="PK",
                                constraint_type="P", column_name="ID", position=1)
    # Act / Assert
    with pytest.raises(ValueError, match="same constraint"):
        mapper.map_constraint([source, source.model_copy(update={"name": "OTHER"})])


def test_map_view_preserves_sql(mapper: OracleMapper) -> None:
    # Arrange
    source = ViewMetadata(schema_name="LIB", name="BOOK_VIEW", definition="SELECT ID FROM BOOKS",
                          columns=[column().model_copy(update={"table_name": "BOOK_VIEW"})])
    # Act
    actual = mapper.map_view(source)
    # Assert
    assert actual.tableType == TableType.View
    assert actual.schemaDefinition is not None
    assert actual.schemaDefinition.root == source.definition


def test_map_table_statistics(mapper: OracleMapper) -> None:
    # Arrange
    source = TableStatisticsMetadata(schema_name="LIB", table_name="BOOKS", object_type="TABLE", num_rows=10)
    # Act
    actual = mapper.map_table_statistics(source, 1700000000000)
    # Assert
    assert actual.rowCount == 10
    assert actual.timestamp.root == 1700000000000


def test_map_column_statistics_does_not_treat_distinct_as_unique(mapper: OracleMapper) -> None:
    # Arrange
    source = ColumnStatisticsMetadata(schema_name="LIB", table_name="BOOKS", column_name="ID",
                                      num_distinct=5, num_nulls=2, low_value=b'\xc1\x02')
    # Act
    actual = mapper.map_column_statistics(source, 1700000000000)
    # Assert
    assert actual.distinctCount == 5
    assert actual.nullCount == 2
    assert actual.uniqueCount is None
    assert actual.min is None


def test_map_view_lineage_direction(mapper: OracleMapper) -> None:
    # Arrange
    source_id, view_id = UUID(int=1), UUID(int=2)
    source = ViewDependencyMetadata(schema_name="LIB", view_name="BOOK_VIEW", view_type="VIEW",
        referenced_schema_name="LIB", referenced_object_name="BOOKS", referenced_object_type="TABLE", dependency_type="HARD")
    # Act
    actual = mapper.map_view_dependency(source, source_id, view_id)
    # Assert
    assert actual.edge.fromEntity.id.root == source_id
    assert actual.edge.toEntity.id.root == view_id


def test_map_synonym(mapper: OracleMapper) -> None:
    # Arrange
    source = SynonymMetadata(schema_name="LIB", name="BOOK_ALIAS", table_owner="LIB", table_name="BOOKS")
    # Act
    actual = mapper.map_synonym(source)
    # Assert
    assert actual.root == "oracle.library.LIB.BOOK_ALIAS"


def test_remote_synonym_requires_resolution(mapper: OracleMapper) -> None:
    # Arrange
    source = SynonymMetadata(schema_name="LIB", name="REMOTE", db_link="REMOTE_DB")
    # Act / Assert
    with pytest.raises(ValueError, match="Remote synonyms"):
        mapper.map_synonym(source)
