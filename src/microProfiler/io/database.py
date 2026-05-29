"""Thread-safe SQLite database operations."""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Literal, Union

import pandas as pd

log = logging.getLogger(__name__)


class Database:
    """Thread-safe SQLite database using WAL mode.

    Each thread gets its own connection to avoid ``sqlite3.ProgrammingError``
    ("SQLite objects created in a thread can only be used in that same thread").
    """

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        log.debug("Database: %s", self.db_path)

    def __del__(self) -> None:
        self.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def close(self) -> None:
        """Close the current thread's connection."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def save_table(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: Literal["fail", "replace", "append"] = "replace",
    ) -> None:
        """Write a DataFrame to an SQLite table.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to persist.
        table_name : str
            Target table name.
        if_exists : str
            ``"fail"``, ``"replace"``, or ``"append"``. Default is ``"replace"``.
        """
        log.debug("save_table: %s (%d rows, %d cols)", table_name, len(df), len(df.columns))
        conn = self._get_conn()
        # Convert Path objects to strings in-place (no copy — caller doesn't reuse df)
        for col in df.columns:
            if df[col].dtype == "object" and len(df) > 0:
                sample = df[col].iloc[0]
                if isinstance(sample, Path):
                    df[col] = df[col].astype(str)
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)

    def query(self, sql: str) -> pd.DataFrame:
        """Execute a SELECT query and return results as a DataFrame.

        Parameters
        ----------
        sql : str
            SQL SELECT statement to execute.

        Returns
        -------
        pd.DataFrame
            Query results.
        """
        conn = self._get_conn()
        return pd.read_sql_query(sql, conn)

    def get_tables(self) -> list:
        """List all tables in the database.

        Returns
        -------
        list of str
            Table names.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]


def write_results_to_db(
    db_path: Path,
    table_name: str,
    results: pd.DataFrame,
    if_exists: str = "append",
) -> None:
    """Convenience: write results using a one-shot Database instance."""
    db = Database(db_path)
    try:
        db.save_table(results, table_name, if_exists=if_exists)
    finally:
        db.close()
