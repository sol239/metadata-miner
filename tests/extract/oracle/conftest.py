"""AAA integration tests against the Oracle database configured in main.ipynb.

Run: .venv/bin/python -m pytest tests/extract/oracle -v
Override the notebook connection with ORACLE_TEST_URL when needed. The account
must be able to create tables, views, sequences, synonyms and triggers and gather
its own optimizer statistics. Fixtures use unique names and are removed afterward.
"""

from collections.abc import Iterator
from typing import Any

import ast
import json
import os
from pathlib import Path
import pytest
from uuid import uuid4

from sqlalchemy import create_engine, text

from core.extract.OracleExtractor import OracleExtractor


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def notebook_url() -> str:
    override = os.environ.get("ORACLE_TEST_URL")
    if override:
        return override
    config_path = PROJECT_ROOT / "config.json"
    if config_path.is_file():
        config = json.loads(config_path.read_text())
        if config.get("METADATA_MINER_ORACLE_URL"):
            return config["METADATA_MINER_ORACLE_URL"]
    notebook = json.loads((PROJECT_ROOT / "main.ipynb").read_text())
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        for node in ast.walk(ast.parse("".join(cell["source"]))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "create_engine" and node.args):
                url = ast.literal_eval(node.args[0])
                if isinstance(url, str):
                    return url
    raise RuntimeError("No literal SQLAlchemy connection URL found in main.ipynb")


class OracleTestContext:
    def prepare(self) -> None:
        self.engine = create_engine(notebook_url())
        self.extractor = OracleExtractor(self.engine)
        self.prefix = "MMT_" + uuid4().hex[:8].upper()
        self.table = self.prefix + "_T"
        self.view = self.prefix + "_V"
        self.sequence = self.prefix + "_S"
        self.synonym = self.prefix + "_ALIAS"
        self.trigger = self.prefix + "_TRG"
        self.index = self.prefix + "_IDX"
        self.created_objects: list[tuple[str, str]] = []
        with self.engine.connect() as conn:
            self.schema = conn.execute(text(
                "SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') FROM dual"
            )).scalar_one()
            self.tablespace = conn.execute(text(
                "SELECT default_tablespace FROM user_users"
            )).scalar_one()
        self.create("TABLE", self.table, f'''
            CREATE TABLE {self.table} (
                id NUMBER(10) CONSTRAINT {self.prefix}_NN NOT NULL,
                code VARCHAR2(20 CHAR),
                parent_id NUMBER(10),
                value NUMBER(10),
                CONSTRAINT {self.prefix}_PK PRIMARY KEY (id),
                CONSTRAINT {self.prefix}_UQ UNIQUE (code),
                CONSTRAINT {self.prefix}_FK FOREIGN KEY (parent_id)
                    REFERENCES {self.table}(id),
                CONSTRAINT {self.prefix}_CK CHECK (value >= 0)
            )''')
        self.execute(f"COMMENT ON TABLE {self.table} IS 'Extractor fixture table'")
        self.execute(f"COMMENT ON COLUMN {self.table}.code IS 'Fixture code'")
        for row_id, code, parent, value in [(1, "A", None, 10), (2, "B", 1, 20), (3, "C", 1, 20)]:
            with self.engine.begin() as conn:
                conn.execute(text(f"INSERT INTO {self.table} VALUES (:id, :code, :parent, :value)"),
                             {"id": row_id, "code": code, "parent": parent, "value": value})
        self.create("INDEX", self.index,
                   f"CREATE INDEX {self.index} ON {self.table}(value DESC, code ASC)")
        # A long definition detects accidental VARCHAR(4000) truncation.
        self.view_definition = "SELECT id, code FROM " + self.table + " WHERE id > 0 /*" + "x" * 5000 + "*/"
        self.create("VIEW", self.view, f"CREATE VIEW {self.view} AS {self.view_definition}")
        self.create("SEQUENCE", self.sequence,
                   f"CREATE SEQUENCE {self.sequence} MINVALUE 1 MAXVALUE 1000 START WITH 1 INCREMENT BY 2 NOCACHE NOCYCLE NOORDER")
        self.create("SYNONYM", self.synonym, f"CREATE SYNONYM {self.synonym} FOR {self.table}")
        self.trigger_definition = f"{self.trigger} BEFORE INSERT ON {self.table} FOR EACH ROW BEGIN NULL; END;"
        self.create("TRIGGER", self.trigger, "CREATE OR REPLACE TRIGGER " + self.trigger_definition)
        with self.engine.begin() as conn:
            conn.execute(text('''BEGIN
                DBMS_STATS.GATHER_TABLE_STATS(
                    ownname => :owner, tabname => :table_name,
                    estimate_percent => 100, method_opt => 'FOR ALL COLUMNS SIZE 254',
                    cascade => TRUE);
                END;'''), {"owner": self.schema, "table_name": self.table})

    def execute(self, sql: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(sql))

    def create(self, kind: str, name: str, sql: str) -> None:
        self.execute(sql)
        self.created_objects.append((kind, name))

    def drop_objects(self) -> None:
        errors: list[tuple[str, Exception]] = []
        for kind, name in reversed(self.created_objects):
            try:
                suffix = " PURGE" if kind == "TABLE" else ""
                self.execute(f"DROP {kind} {name}{suffix}")
            except Exception as error:
                errors.append((name, error))
        if errors:
            raise RuntimeError(f"Could not clean up Oracle fixtures: {errors}")

    def reference(self, sql: str, **params: object) -> dict[str, Any]:
        with self.engine.connect() as conn:
            return dict(conn.execute(text(sql), params).mappings().one())


@pytest.fixture(scope="module")
def oracle() -> Iterator[OracleTestContext]:
    context = OracleTestContext()
    context.created_objects = []
    try:
        context.prepare()
        yield context
    finally:
        try:
            context.drop_objects()
        finally:
            if hasattr(context, "engine"):
                context.engine.dispose()
