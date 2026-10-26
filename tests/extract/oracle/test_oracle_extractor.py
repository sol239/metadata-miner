"""Oracle extraction integration tests using explicit models and AAA."""

from typing import TypedDict

import pytest

from conftest import OracleTestContext

from core.cdm import (
    ColumnMetadata, ColumnStatisticsMetadata, ConstraintMetadata, HistogramMetadata,
    IndexMetadata, ObjectMetadata, SequenceMetadata, SynonymMetadata, TableMetadata,
    TableStatisticsMetadata, TriggerMetadata, UserMetadata, ViewDependencyMetadata,
    ViewMetadata,
)
from core.extract.OracleExtractor import MetadataAccessError, OracleExtractor



class DictionaryAccessProbe(OracleExtractor):
    def read_missing_dictionary(self, schema_name: str) -> None:
        self._read_sql(
            "SELECT * FROM all_mmt_missing_dictionary WHERE owner = :schema",
            schema_name,
        )


class ConstraintContext(TypedDict):
    schema_name: str
    table_name: str
    status: str
    deferrable: str
    deferred: str
    validated: str


def expected_columns(oracle: OracleTestContext, object_name: str, is_view: bool = False) -> list[ColumnMetadata]:
    specs = [("ID", 1, False), ("CODE", 2, True)]
    if not is_view:
        specs += [("PARENT_ID", 3, True), ("VALUE", 4, True)]
    return [ColumnMetadata(
        schema_name=oracle.schema, table_name=object_name, name=name,
        data_type="VARCHAR2" if name == "CODE" else "NUMBER",
        nullable=nullable, position=position,
        description="Fixture code" if name == "CODE" and not is_view else None,
        data_length=80 if name == "CODE" else 22,
        data_precision=None if name == "CODE" else 10,
        data_scale=None if name == "CODE" else 0,
        char_length=20 if name == "CODE" else 0,
        char_used="C" if name == "CODE" else None,
    ) for name, position, nullable in specs]


def expected_constraints(oracle: OracleTestContext) -> list[ConstraintMetadata]:
    common = ConstraintContext(schema_name=oracle.schema, table_name=oracle.table, status="ENABLED",
        deferrable="NOT DEFERRABLE", deferred="IMMEDIATE", validated="VALIDATED")
    expected = [
        ConstraintMetadata(**common, name=oracle.prefix+"_CK", constraint_type="C",
            search_condition_vc="value >= 0", column_name="VALUE"),
        ConstraintMetadata(**common, name=oracle.prefix+"_NN", constraint_type="C",
            search_condition_vc='"ID" IS NOT NULL', column_name="ID"),
        ConstraintMetadata(**common, name=oracle.prefix+"_PK", constraint_type="P", column_name="ID", position=1),
        ConstraintMetadata(**common, name=oracle.prefix+"_FK", constraint_type="R", column_name="PARENT_ID", position=1,
            referenced_schema_name=oracle.schema, referenced_table_name=oracle.table,
            referenced_column_name="ID", delete_rule="NO ACTION"),
        ConstraintMetadata(**common, name=oracle.prefix+"_UQ", constraint_type="U", column_name="CODE", position=1),
    ]
    return expected


def expected_indexes(oracle: OracleTestContext) -> list[IndexMetadata]:
    hidden = oracle.reference("""SELECT column_name FROM all_ind_columns
        WHERE index_owner = :owner AND index_name = :name AND column_position = 1""",
        owner=oracle.schema, name=oracle.index)["column_name"]
    specs = [
        (oracle.index, "FUNCTION-BASED NORMAL", "NONUNIQUE", hidden, 1, "DESC"),
        (oracle.index, "FUNCTION-BASED NORMAL", "NONUNIQUE", "CODE", 2, "ASC"),
        (oracle.prefix + "_PK", "NORMAL", "UNIQUE", "ID", 1, "ASC"),
        (oracle.prefix + "_UQ", "NORMAL", "UNIQUE", "CODE", 1, "ASC"),
    ]
    return [IndexMetadata(name=name, index_type=kind, owner=oracle.schema,
        table_owner=oracle.schema, table_name=oracle.table, uniqueness=unique,
        column_name=column, position=position, sort_order=order,
        description="Extractor fixture table")
        for name, kind, unique, column, position, order in sorted(specs, key=lambda item: (item[0], item[4]))]


def test_extract_users(oracle: OracleTestContext) -> None:
    # Arrange
    row = oracle.reference("SELECT user_id, created FROM all_users WHERE username = :name", name=oracle.schema)
    expected = UserMetadata(schema_name=oracle.schema, user_id=row["user_id"], created=row["created"])
    # Act
    actual = oracle.extractor.extract_users(oracle.schema)
    # Assert
    assert actual == [expected]


def test_extract_objects(oracle: OracleTestContext) -> None:
    # Arrange
    row = oracle.reference("""SELECT object_id, created, last_ddl_time FROM all_objects
        WHERE owner = :owner AND object_name = :name AND object_type = 'TABLE'""",
        owner=oracle.schema, name=oracle.table)
    expected = ObjectMetadata(schema_name=oracle.schema, name=oracle.table,
        object_type="TABLE", object_id=row["object_id"], status="VALID",
        created=row["created"], last_ddl_time=row["last_ddl_time"],
        temporary=False, generated=False)
    # Act
    actual = oracle.extractor.extract_objects(oracle.schema)
    # Assert
    assert [item for item in actual if item.name == oracle.table and item.object_type == 'TABLE'] == [expected]


def test_extract_tables(oracle: OracleTestContext) -> None:
    # Arrange
    expected = TableMetadata(schema_name=oracle.schema, name=oracle.table,
        tablespace_name=oracle.tablespace, status="VALID", temporary=False,
        partitioned=False, nested=False, description="Extractor fixture table",
        columns=expected_columns(oracle, oracle.table),
        constraints=expected_constraints(oracle), indexes=expected_indexes(oracle))
    # Act
    actual = oracle.extractor.extract_tables(oracle.schema)
    # Assert
    assert [item for item in actual if item.name == oracle.table] == [expected]


def test_extract_columns(oracle: OracleTestContext) -> None:
    # Arrange
    expected = ColumnMetadata(schema_name=oracle.schema, table_name=oracle.table,
        name="CODE", data_type="VARCHAR2", nullable=True, position=2,
        description="Fixture code", data_length=80, char_length=20, char_used="C")
    # Act
    actual = oracle.extractor.extract_columns(oracle.schema)
    # Assert
    assert [item for item in actual if item.table_name == oracle.table and item.name == 'CODE'] == [expected]


def test_extract_views(oracle: OracleTestContext) -> None:
    # Arrange
    expected = ViewMetadata(schema_name=oracle.schema, name=oracle.view,
        text_length=len(oracle.view_definition), definition=oracle.view_definition, read_only=False,
        columns=expected_columns(oracle, oracle.view, is_view=True),
        dependencies=[ViewDependencyMetadata(schema_name=oracle.schema, view_name=oracle.view,
            view_type="VIEW", referenced_schema_name=oracle.schema,
            referenced_object_name=oracle.table, referenced_object_type="TABLE", dependency_type="HARD")])
    # Act
    actual = oracle.extractor.extract_views(oracle.schema)
    # Assert
    assert [item for item in actual if item.name == oracle.view] == [expected]
    assert expected.definition is not None
    assert len(expected.definition) > 4000


def test_extract_indexes(oracle: OracleTestContext) -> None:
    # Arrange
    hidden = oracle.reference("""SELECT column_name FROM all_ind_columns
        WHERE index_owner = :owner AND index_name = :name AND column_position = 1""",
        owner=oracle.schema, name=oracle.index)["column_name"]
    expected = [IndexMetadata(name=oracle.index, index_type="FUNCTION-BASED NORMAL",
        owner=oracle.schema, table_owner=oracle.schema, table_name=oracle.table,
        uniqueness="NONUNIQUE", column_name=column, position=position,
        sort_order=order, description="Extractor fixture table")
        for column, position, order in [(hidden, 1, "DESC"), ("CODE", 2, "ASC")]]
    # Act
    actual = oracle.extractor.extract_indexes(oracle.schema)
    # Assert
    assert [item for item in actual if item.name == oracle.index] == expected


def test_extract_triggers(oracle: OracleTestContext) -> None:
    # Arrange
    expected = TriggerMetadata(schema_name=oracle.schema, name=oracle.trigger,
        trigger_type="BEFORE EACH ROW", triggering_event="INSERT", base_object_type="TABLE",
        table_owner=oracle.schema, table_name=oracle.table,
        referencing_names="REFERENCING NEW AS NEW OLD AS OLD", status="ENABLED",
        description=oracle.trigger_definition.split("BEGIN")[0],
        action_type="PL/SQL", trigger_body="BEGIN NULL; END;")
    # Act
    actual = oracle.extractor.extract_triggers(oracle.schema)
    # Assert
    assert [item for item in actual if item.name == oracle.trigger] == [expected]


def test_extract_sequences(oracle: OracleTestContext) -> None:
    # Arrange
    expected = SequenceMetadata(schema_name=oracle.schema, name=oracle.sequence,
        min_value=1, max_value=1000, increment_by=2, cycle_flag=False,
        order_flag=False, cache_size=0, last_number=1)
    # Act
    actual = oracle.extractor.extract_sequences(oracle.schema)
    # Assert
    assert [item for item in actual if item.name == oracle.sequence] == [expected]


def test_extract_synonyms(oracle: OracleTestContext) -> None:
    # Arrange
    expected = SynonymMetadata(schema_name=oracle.schema, name=oracle.synonym,
        table_owner=oracle.schema, table_name=oracle.table)
    # Act
    actual = oracle.extractor.extract_synonyms(oracle.schema)
    # Assert
    assert [item for item in actual if item.name == oracle.synonym] == [expected]


def test_extract_table_statistics(oracle: OracleTestContext) -> None:
    # Arrange
    row = oracle.reference("""SELECT blocks, empty_blocks, avg_row_len, last_analyzed
        FROM all_tab_statistics WHERE owner = :owner AND table_name = :name
        AND object_type = 'TABLE'""", owner=oracle.schema, name=oracle.table)
    expected = TableStatisticsMetadata(schema_name=oracle.schema, table_name=oracle.table,
        object_type="TABLE", num_rows=3, blocks=row["blocks"], empty_blocks=row["empty_blocks"],
        avg_row_len=row["avg_row_len"], sample_size=3, last_analyzed=row["last_analyzed"],
        stale_stats=False, global_stats=True)
    # Act
    actual = oracle.extractor.extract_table_statistics(oracle.schema)
    # Assert
    assert [item for item in actual if item.table_name == oracle.table] == [expected]


def test_extract_column_statistics(oracle: OracleTestContext) -> None:
    # Arrange
    expected = ColumnStatisticsMetadata(schema_name=oracle.schema, table_name=oracle.table,
        column_name="PARENT_ID", num_distinct=1, num_nulls=1,
        low_value=bytes.fromhex("C102"), high_value=bytes.fromhex("C102"),
        density=0.25, avg_col_len=3, sample_size=2)
    # Act
    actual = oracle.extractor.extract_column_statistics(oracle.schema)
    # Assert
    assert [item for item in actual if item.table_name == oracle.table and item.column_name == 'PARENT_ID'] == [expected]


def test_extract_histograms(oracle: OracleTestContext) -> None:
    # Arrange
    expected = [HistogramMetadata(schema_name=oracle.schema, table_name=oracle.table,
        column_name="VALUE", endpoint_number=number, endpoint_value=value,
        endpoint_actual_value=str(value),
        endpoint_actual_value_raw=raw,
        endpoint_repeat_count=0)
        for number, value, raw in [(1, 10, bytes.fromhex("C10B")), (3, 20, bytes.fromhex("C115"))]]
    # Act
    actual = oracle.extractor.extract_histograms(oracle.schema)
    # Assert
    assert [item for item in actual if item.table_name == oracle.table and item.column_name == 'VALUE'] == expected


def test_extract_constraints(oracle: OracleTestContext) -> None:
    # Arrange
    common = ConstraintContext(schema_name=oracle.schema, table_name=oracle.table, status="ENABLED",
        deferrable="NOT DEFERRABLE", deferred="IMMEDIATE", validated="VALIDATED")
    expected = [
        ConstraintMetadata(**common, name=oracle.prefix+"_CK", constraint_type="C",
            search_condition_vc="value >= 0", column_name="VALUE"),
        ConstraintMetadata(**common, name=oracle.prefix+"_NN", constraint_type="C",
            search_condition_vc='"ID" IS NOT NULL', column_name="ID"),
        ConstraintMetadata(**common, name=oracle.prefix+"_PK", constraint_type="P", column_name="ID", position=1),
        ConstraintMetadata(**common, name=oracle.prefix+"_FK", constraint_type="R", column_name="PARENT_ID", position=1,
            referenced_schema_name=oracle.schema, referenced_table_name=oracle.table,
            referenced_column_name="ID", delete_rule="NO ACTION"),
        ConstraintMetadata(**common, name=oracle.prefix+"_UQ", constraint_type="U", column_name="CODE", position=1),
    ]
    # Act
    actual = oracle.extractor.extract_constraints(oracle.schema)
    # Assert
    assert [item for item in actual if item.table_name == oracle.table] == expected


def test_extract_view_dependencies(oracle: OracleTestContext) -> None:
    # Arrange
    expected = ViewDependencyMetadata(schema_name=oracle.schema, view_name=oracle.view,
        view_type="VIEW", referenced_schema_name=oracle.schema,
        referenced_object_name=oracle.table, referenced_object_type="TABLE", dependency_type="HARD")
    # Act
    actual = oracle.extractor.extract_view_dependencies(oracle.schema)
    # Assert
    assert [item for item in actual if item.view_name == oracle.view] == [expected]


@pytest.mark.parametrize("method_name", [
    "extract_users", "extract_objects", "extract_tables", "extract_columns",
    "extract_views", "extract_indexes", "extract_triggers", "extract_sequences",
    "extract_synonyms", "extract_table_statistics", "extract_column_statistics",
    "extract_histograms", "extract_constraints", "extract_view_dependencies",
])
def test_empty_schema_results_preserve_unknown_visibility(oracle: OracleTestContext, method_name: str) -> None:
    # Arrange
    expected: list[object] = []
    # Act
    actual = getattr(oracle.extractor, method_name)(oracle.prefix + "_ABSENT")
    # Assert
    assert actual == expected
    model_name = {
        "extract_users": "UserMetadata", "extract_objects": "ObjectMetadata",
        "extract_tables": "TableMetadata", "extract_columns": "ColumnMetadata",
        "extract_views": "ViewMetadata", "extract_indexes": "IndexMetadata",
        "extract_triggers": "TriggerMetadata", "extract_sequences": "SequenceMetadata",
        "extract_synonyms": "SynonymMetadata", "extract_table_statistics": "TableStatisticsMetadata",
        "extract_column_statistics": "ColumnStatisticsMetadata", "extract_histograms": "HistogramMetadata",
        "extract_constraints": "ConstraintMetadata", "extract_view_dependencies": "ViewDependencyMetadata",
    }[method_name]
    assert oracle.extractor.extraction_info[model_name]["metadata_result"] == "empty_or_inaccessible"


def test_missing_dictionary_view_raises_access_error(oracle: OracleTestContext) -> None:
    # Arrange
    probe = DictionaryAccessProbe(oracle.engine)
    # Act
    with pytest.raises(MetadataAccessError) as caught:
        probe.read_missing_dictionary(oracle.schema)
    # Assert
    assert caught.value.oracle_code == 942
    assert caught.value.schema_name == oracle.schema

