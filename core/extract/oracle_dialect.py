"""Support python-oracledb with the SQLAlchemy 1.4 required by OM 1.12."""

from types import SimpleNamespace

import oracledb
import sqlalchemy
from sqlalchemy.dialects import registry
from sqlalchemy.dialects.oracle.cx_oracle import OracleDialect_cx_oracle


class OracleDialect_oracledb(OracleDialect_cx_oracle):
    driver = "oracledb"
    supports_statement_cache = True

    @classmethod
    def dbapi(cls):
        # The 1.4 dialect checks the cx_Oracle version; keep the real module intact.
        attributes = dict(vars(oracledb))
        attributes["version"] = "8.3.0"
        return SimpleNamespace(**attributes)


def register_oracle_dialect() -> None:
    if sqlalchemy.__version__.startswith("1.4."):
        registry.register(
            "oracle.oracledb", __name__, "OracleDialect_oracledb"
        )
