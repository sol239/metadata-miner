"""Verify assembly joins use schema and object name, with bulk extraction."""

from unittest.mock import Mock

import pandas as pd
from pytest import MonkeyPatch
from sqlalchemy import create_engine

from core.cdm import ColumnMetadata, TableMetadata, ViewMetadata
from core.extract.OracleExtractor import OracleExtractor


def test_table_assembly_matches_schema_and_keeps_empty_children(monkeypatch: MonkeyPatch) -> None:
    # Arrange
    engine = create_engine("sqlite://")
    extractor = OracleExtractor(engine)
    column = ColumnMetadata(schema_name="ONE", table_name="SHARED", name="ID",
                            data_type="NUMBER", nullable=False, position=1)
    other_column = column.model_copy(update={"schema_name": "OTHER"})
    expected = [TableMetadata(schema_name="ONE", name="SHARED", columns=[column]),
                TableMetadata(schema_name="ONE", name="EMPTY")]
    monkeypatch.setattr(extractor, "_read_sql", Mock(return_value=pd.DataFrame([
        {"schema_name": "ONE", "table_name": "SHARED"},
        {"schema_name": "ONE", "table_name": "EMPTY"},
    ])))
    columns = Mock(return_value=[column, other_column])
    constraints = Mock(return_value=[])
    indexes = Mock(return_value=[])
    monkeypatch.setattr(extractor, "extract_columns", columns)
    monkeypatch.setattr(extractor, "extract_constraints", constraints)
    monkeypatch.setattr(extractor, "extract_indexes", indexes)
    try:
        # Act
        actual = extractor.extract_tables("ONE")
        # Assert
        assert actual == expected
        for child_extractor in [columns, constraints, indexes]:
            child_extractor.assert_called_once_with("ONE")
        assert actual[0].constraints is not actual[1].constraints
    finally:
        engine.dispose()


def test_view_assembly_matches_schema_and_keeps_empty_children(monkeypatch: MonkeyPatch) -> None:
    # Arrange
    engine = create_engine("sqlite://")
    extractor = OracleExtractor(engine)
    column = ColumnMetadata(schema_name="ONE", table_name="SHARED", name="ID",
                            data_type="NUMBER", nullable=False, position=1)
    other_column = column.model_copy(update={"schema_name": "OTHER"})
    expected = [ViewMetadata(schema_name="ONE", name="SHARED", columns=[column]),
                ViewMetadata(schema_name="ONE", name="EMPTY")]
    monkeypatch.setattr(extractor, "_read_sql", Mock(return_value=pd.DataFrame([
        {"schema_name": "ONE", "view_name": "SHARED"},
        {"schema_name": "ONE", "view_name": "EMPTY"},
    ])))
    columns = Mock(return_value=[column, other_column])
    dependencies = Mock(return_value=[])
    monkeypatch.setattr(extractor, "extract_columns", columns)
    monkeypatch.setattr(extractor, "extract_view_dependencies", dependencies)
    try:
        # Act
        actual = extractor.extract_views("ONE")
        # Assert
        assert actual == expected
        columns.assert_called_once_with("ONE")
        dependencies.assert_called_once_with("ONE")
        assert actual[0].dependencies is not actual[1].dependencies
    finally:
        engine.dispose()
