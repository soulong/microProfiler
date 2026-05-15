from __future__ import annotations

import pandas as pd
import pytest

from microProfiler.io.database import Database, write_results_to_db


@pytest.fixture
def db(temp_dir):
    path = temp_dir / "test.db"
    db = Database(path)
    yield db
    db.close()


class TestDatabase:
    def test_save_and_query(self, db):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        db.save_table(df, "test_table")
        result = db.query("SELECT * FROM test_table ORDER BY a")
        assert len(result) == 3
        assert result["a"].tolist() == [1, 2, 3]

    def test_get_tables(self, db):
        df = pd.DataFrame({"x": [1]})
        db.save_table(df, "table1")
        db.save_table(pd.DataFrame({"y": [2]}), "table2")
        tables = db.get_tables()
        assert "table1" in tables
        assert "table2" in tables

    def test_append_mode(self, db):
        df1 = pd.DataFrame({"a": [1]})
        df2 = pd.DataFrame({"a": [2]})
        db.save_table(df1, "append_table", if_exists="append")
        db.save_table(df2, "append_table", if_exists="append")
        result = db.query("SELECT * FROM append_table ORDER BY a")
        assert result["a"].tolist() == [1, 2]

    def test_replace_mode(self, db):
        df1 = pd.DataFrame({"a": [1]})
        df2 = pd.DataFrame({"a": [2]})
        db.save_table(df1, "rep_table")
        db.save_table(df2, "rep_table", if_exists="replace")
        result = db.query("SELECT * FROM rep_table")
        assert result["a"].tolist() == [2]

    def test_close_and_reopen(self, temp_dir):
        path = temp_dir / "close_test.db"
        db = Database(path)
        db.save_table(pd.DataFrame({"a": [1]}), "t")
        db.close()
        db2 = Database(path)
        result = db2.query("SELECT * FROM t")
        assert len(result) == 1
        db2.close()

    def test_database_creates_parent_dir(self, temp_dir):
        nested = temp_dir / "sub" / "nested" / "test.db"
        db = Database(nested)
        db.save_table(pd.DataFrame({"a": [1]}), "t")
        assert nested.exists()
        db.close()

    def test_convenience_function(self, temp_dir):
        path = temp_dir / "convenience.db"
        df = pd.DataFrame({"x": [10, 20]})
        write_results_to_db(path, "results", df, if_exists="replace")
        db = Database(path)
        result = db.query("SELECT * FROM results")
        assert len(result) == 2
        db.close()


class TestWALMode:
    def test_wal_enabled(self, temp_dir):
        path = temp_dir / "wal_test.db"
        db = Database(path)
        # Force a write to ensure WAL mode is committed
        db.save_table(pd.DataFrame({"a": [1]}), "test")
        result = db.query("PRAGMA journal_mode")
        mode = result.iloc[0, 0]
        assert mode == "wal"
        db.close()
