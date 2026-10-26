"""Oracle implementation of the SQL metadata extraction interface."""

import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Protocol, TypeVar, cast

import oracledb
import pandas as pd
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from core.extract.oracle_dialect import register_oracle_dialect

register_oracle_dialect()
from sqlalchemy.exc import DBAPIError

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
from core.cdm.metadata_normalizer import MetadataNormalizer

from .ISQLExtractor import ISQLExtractor

T = TypeVar("T", bound=BaseModel)


class _CatalogCursor(Protocol):
    @property
    def description(self) -> Sequence[Sequence[object]] | None: ...

    def execute(self, statement: str, parameters: dict[str, str]) -> object: ...

    def fetchall(self) -> list[tuple[object, ...]]: ...


class MetadataAccessError(RuntimeError):
    """A catalog query was denied or its dictionary view was unavailable."""

    def __init__(self, schema_name: str, catalogs: list[str], code: int) -> None:
        self.schema_name = schema_name
        self.catalogs = catalogs
        self.oracle_code = code
        super().__init__(
            f"Cannot access metadata for schema {schema_name!r} from "
            f"{', '.join(catalogs)} (ORA-{code:05d}). "
            "The dictionary view may be unavailable or privileges insufficient."
        )


class OracleExtractor(ISQLExtractor):
    """Extract Oracle catalog metadata into validated Pydantic models.

    Dictionary access errors raise :class:`MetadataAccessError`. The
    ``extraction_info`` dictionary stores visibility and completeness by model name;
    empty results for another schema are not proof that its objects are absent.

    Args:
        engine: SQLAlchemy engine connected to the Oracle database. The
            extractor reuses this engine and does not dispose it.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self.extraction_info: dict[str, dict[str, object]] = {}

    @staticmethod
    def _default_output_type(
        _cursor: oracledb.Cursor, _metadata: oracledb.FetchInfo
    ) -> None:
        return None

    def _read_sql(
        self, query: str, schema_name: str, *, fetch_long: bool = False
    ) -> pd.DataFrame:
        try:
            with self._engine.connect() as connection:
                session_user = connection.execute(
                    text("SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') FROM dual")
                ).scalar_one()
                if fetch_long:
                    driver_connection = connection.connection.driver_connection
                    if not isinstance(driver_connection, oracledb.Connection):
                        raise TypeError(
                            "LONG fetching requires a python-oracledb connection."
                        )
                    with driver_connection.cursor() as cursor:
                        cursor.outputtypehandler = self._default_output_type
                        catalog_cursor = cast(_CatalogCursor, cursor)
                        catalog_cursor.execute(query, {"schema": schema_name})
                        description = catalog_cursor.description
                        if description is None:
                            raise RuntimeError("Catalog query returned no result columns.")
                        columns = [str(item[0]).lower() for item in description]
                        frame = pd.DataFrame.from_records(
                            catalog_cursor.fetchall(), columns=columns
                        )
                else:
                    result = connection.execute(text(query), {"schema": schema_name})
                    frame = pd.DataFrame.from_records(
                        result.fetchall(), columns=list(result.keys())
                    )
        except (DBAPIError, oracledb.DatabaseError, pd.errors.DatabaseError) as error:
            original: BaseException = error
            while isinstance(original, pd.errors.DatabaseError):
                cause = original.__cause__
                if cause is None:
                    break
                original = cause
            if isinstance(original, DBAPIError):
                driver_error = original.orig
                if driver_error is not None:
                    original = driver_error
            detail = original.args[0] if original.args else original
            code = getattr(detail, "code", None)
            if code in {942, 1031}:
                catalogs = sorted(set(re.findall(r"\ball_[a-z_]+\b", query, re.I)))
                raise MetadataAccessError(schema_name, catalogs, code) from error
            raise
        frame.attrs.update(
            metadata_visibility="accessible_objects_only",
            schema_name=schema_name,
            session_user=session_user,
            metadata_completeness=(
                "schema_owner" if schema_name == session_user else "unknown"
            ),
            metadata_result=(
                "empty"
                if frame.empty and schema_name == session_user
                else "empty_or_inaccessible" if frame.empty else "available"
            ),
        )
        return frame

    def _normalize(
        self,
        frame: pd.DataFrame,
        model: type[T],
        field_mapping: dict[str, str] | None = None,
    ) -> list[T]:
        records = MetadataNormalizer.normalize(frame, model, field_mapping)
        self.extraction_info[model.__name__] = {
            str(key): value for key, value in frame.attrs.items()
        }
        return records

    def extract_users(self, schema_name: str) -> list[UserMetadata]:
        users_sql = """
        SELECT
            username AS schema_name,
            user_id,
            created
        FROM all_users
        WHERE username = :schema
        ORDER BY username
        """
        return self._normalize(
            self._read_sql(users_sql, schema_name),
            UserMetadata,
        )

    def extract_objects(self, schema_name: str) -> list[ObjectMetadata]:
        objects_sql = """
        SELECT
            owner AS schema_name,
            object_name,
            subobject_name,
            object_id,
            object_type,
            status,
            created,
            last_ddl_time,
            temporary,
            generated
        FROM all_objects
        WHERE owner = :schema
        ORDER BY owner, object_type, object_name, subobject_name
        """
        return self._normalize(
            self._read_sql(objects_sql, schema_name),
            ObjectMetadata,
            {"object_name": "name"},
        )

    def extract_tables(self, schema_name: str) -> list[TableMetadata]:
        tables_sql = """
        SELECT
            t.owner AS schema_name,
            t.table_name,
            t.tablespace_name,
            t.status,
            t.temporary,
            t.partitioned,
            t.iot_type,
            t.nested,
            comments.comments AS table_comment
        FROM all_tables t
        LEFT JOIN all_tab_comments comments
            ON comments.owner = t.owner
            AND comments.table_name = t.table_name
        WHERE t.owner = :schema
        ORDER BY t.owner, t.table_name
        """
        tables = self._normalize(
            self._read_sql(tables_sql, schema_name),
            TableMetadata,
            {"table_name": "name", "table_comment": "description"},
        )
        if not tables:
            return tables
        columns: dict[tuple[str, str], list[ColumnMetadata]] = defaultdict(list)
        constraints: dict[tuple[str, str], list[ConstraintMetadata]] = defaultdict(list)
        indexes: dict[tuple[str, str], list[IndexMetadata]] = defaultdict(list)
        for column in self.extract_columns(schema_name):
            columns[column.schema_name, column.table_name].append(column)
        for constraint in self.extract_constraints(schema_name):
            constraints[constraint.schema_name, constraint.table_name].append(constraint)
        for index in self.extract_indexes(schema_name):
            indexes[index.table_owner, index.table_name].append(index)
        for table in tables:
            key = (table.schema_name, table.name)
            table.columns = columns[key]
            table.constraints = constraints[key]
            table.indexes = indexes[key]
        return tables

    def extract_columns(self, schema_name: str) -> list[ColumnMetadata]:
        columns_sql = """
        SELECT
            c.owner AS schema_name,
            c.table_name,
            c.column_id,
            c.column_name,
            c.data_type,
            c.data_type_owner,
            c.data_length,
            c.data_precision,
            c.data_scale,
            c.char_length,
            c.char_used,
            c.nullable,
            c.data_default,
            comments.comments AS column_comment
        FROM all_tab_columns c
        LEFT JOIN all_col_comments comments
            ON comments.owner = c.owner
            AND comments.table_name = c.table_name
            AND comments.column_name = c.column_name
        WHERE c.owner = :schema
        ORDER BY c.owner, c.table_name, c.column_id
        """
        return self._normalize(
            self._read_sql(columns_sql, schema_name),
            ColumnMetadata,
            {
                "column_name": "name",
                "column_id": "position",
                "column_comment": "description",
                "data_default": "default_value",
            },
        )

    def extract_views(self, schema_name: str) -> list[ViewMetadata]:
        views_sql = """
        SELECT
            owner AS schema_name,
            view_name,
            text_length,
            text AS view_definition,
            read_only
        FROM all_views
        WHERE owner = :schema
        ORDER BY owner, view_name
        """
        views = self._normalize(
            self._read_sql(views_sql, schema_name, fetch_long=True),
            ViewMetadata,
            {"view_name": "name", "view_definition": "definition"},
        )
        if not views:
            return views
        columns: dict[tuple[str, str], list[ColumnMetadata]] = defaultdict(list)
        dependencies: dict[tuple[str, str], list[ViewDependencyMetadata]] = defaultdict(list)
        for column in self.extract_columns(schema_name):
            columns[column.schema_name, column.table_name].append(column)
        for dependency in self.extract_view_dependencies(schema_name):
            dependencies[dependency.schema_name, dependency.view_name].append(dependency)
        for view in views:
            key = (view.schema_name, view.name)
            view.columns = columns[key]
            view.dependencies = dependencies[key]
        return views

    def extract_indexes(self, schema_name: str) -> list[IndexMetadata]:
        indexes_sql = """
        SELECT
            i.index_name,
            i.index_type,
            i.owner,
            i.table_owner,
            i.table_name,
            i.uniqueness,
            ic.column_name,
            ic.column_position,
            ic.descend AS sort_order,
            comments.comments AS table_comment
        FROM all_indexes i
        LEFT JOIN all_ind_columns ic
            ON ic.index_owner = i.owner
            AND ic.index_name = i.index_name
            AND ic.table_owner = i.table_owner
            AND ic.table_name = i.table_name
        LEFT JOIN all_tab_comments comments
            ON comments.owner = i.table_owner
            AND comments.table_name = i.table_name
        WHERE i.table_owner = :schema
        ORDER BY i.table_name, i.index_name, ic.column_position
        """
        return self._normalize(
            self._read_sql(indexes_sql, schema_name),
            IndexMetadata,
            {
                "index_name": "name",
                "column_position": "position",
                "table_comment": "description",
            },
        )

    def extract_triggers(self, schema_name: str) -> list[TriggerMetadata]:
        triggers_sql = """
        SELECT
            owner AS schema_name,
            trigger_name,
            trigger_type,
            triggering_event,
            base_object_type,
            table_owner,
            table_name,
            column_name,
            referencing_names,
            when_clause,
            status,
            description,
            TRIM(action_type) AS action_type,
            trigger_body
        FROM all_triggers
        WHERE owner = :schema
        ORDER BY owner, trigger_name
        """
        return self._normalize(
            self._read_sql(triggers_sql, schema_name),
            TriggerMetadata,
            {"trigger_name": "name"},
        )

    def extract_sequences(self, schema_name: str) -> list[SequenceMetadata]:
        sequences_sql = """
        SELECT
            sequence_owner AS schema_name,
            sequence_name,
            min_value,
            max_value,
            increment_by,
            cycle_flag,
            order_flag,
            cache_size,
            last_number
        FROM all_sequences
        WHERE sequence_owner = :schema
        ORDER BY sequence_owner, sequence_name
        """
        return self._normalize(
            self._read_sql(sequences_sql, schema_name),
            SequenceMetadata,
            {"sequence_name": "name"},
        )

    def extract_synonyms(self, schema_name: str) -> list[SynonymMetadata]:
        synonyms_sql = """
        SELECT
            owner AS schema_name,
            synonym_name,
            table_owner,
            table_name,
            db_link
        FROM all_synonyms
        WHERE owner = :schema
        ORDER BY owner, synonym_name
        """
        return self._normalize(
            self._read_sql(synonyms_sql, schema_name),
            SynonymMetadata,
            {"synonym_name": "name"},
        )

    def extract_table_statistics(
        self, schema_name: str
    ) -> list[TableStatisticsMetadata]:
        table_statistics_sql = """
        SELECT
            owner AS schema_name,
            table_name,
            object_type,
            num_rows,
            blocks,
            empty_blocks,
            avg_row_len,
            sample_size,
            last_analyzed,
            stale_stats,
            global_stats
        FROM all_tab_statistics
        WHERE owner = :schema
        ORDER BY owner, table_name, object_type
        """
        return self._normalize(
            self._read_sql(table_statistics_sql, schema_name),
            TableStatisticsMetadata,
        )

    def extract_column_statistics(
        self, schema_name: str
    ) -> list[ColumnStatisticsMetadata]:
        column_statistics_sql = """
        SELECT
            owner AS schema_name,
            table_name,
            column_name,
            num_distinct,
            num_nulls,
            low_value,
            high_value,
            density,
            avg_col_len,
            sample_size
        FROM all_tab_col_statistics
        WHERE owner = :schema
        ORDER BY owner, table_name, column_name
        """
        return self._normalize(
            self._read_sql(column_statistics_sql, schema_name),
            ColumnStatisticsMetadata,
        )

    def extract_histograms(self, schema_name: str) -> list[HistogramMetadata]:
        histograms_sql = """
        SELECT
            owner AS schema_name,
            table_name,
            column_name,
            endpoint_number,
            endpoint_value,
            endpoint_actual_value,
            endpoint_actual_value_raw,
            endpoint_repeat_count
        FROM all_tab_histograms
        WHERE owner = :schema
        ORDER BY owner, table_name, column_name, endpoint_number
        """
        return self._normalize(
            self._read_sql(histograms_sql, schema_name),
            HistogramMetadata,
        )

    def extract_constraints(self, schema_name: str) -> list[ConstraintMetadata]:
        constraints_sql = """
        SELECT
            c.owner AS schema_name,
            c.table_name,
            c.constraint_name,
            c.constraint_type,
            c.search_condition_vc,
            cc.column_name,
            cc.position AS column_position,
            c.r_owner AS referenced_schema_name,
            rc.table_name AS referenced_table_name,
            rcc.column_name AS referenced_column_name,
            c.delete_rule,
            c.status,
            c.deferrable,
            c.deferred,
            c.validated
        FROM all_constraints c
        LEFT JOIN all_cons_columns cc
            ON cc.owner = c.owner
            AND cc.constraint_name = c.constraint_name
            AND cc.table_name = c.table_name
        LEFT JOIN all_constraints rc
            ON rc.owner = c.r_owner
            AND rc.constraint_name = c.r_constraint_name
        LEFT JOIN all_cons_columns rcc
            ON rcc.owner = rc.owner
            AND rcc.constraint_name = rc.constraint_name
            AND rcc.table_name = rc.table_name
            AND rcc.position = cc.position
        WHERE c.owner = :schema
            AND c.constraint_type IN ('P', 'R', 'U', 'C')
        ORDER BY c.table_name, c.constraint_type, c.constraint_name, cc.position
        """
        return self._normalize(
            self._read_sql(constraints_sql, schema_name),
            ConstraintMetadata,
            {"constraint_name": "name", "column_position": "position"},
        )

    def extract_view_dependencies(
        self, schema_name: str
    ) -> list[ViewDependencyMetadata]:
        view_dependencies_sql = """
        SELECT
            owner AS schema_name,
            name AS view_name,
            type AS view_type,
            referenced_owner AS referenced_schema_name,
            referenced_name AS referenced_object_name,
            referenced_type AS referenced_object_type,
            dependency_type
        FROM all_dependencies
        WHERE owner = :schema
            AND type = 'VIEW'
        ORDER BY owner, name, referenced_owner, referenced_name
        """
        return self._normalize(
            self._read_sql(view_dependencies_sql, schema_name),
            ViewDependencyMetadata,
        )
