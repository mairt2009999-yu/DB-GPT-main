#!/usr/bin/env python3
"""Database connection utility for SQL Data Analyzer.

Supports SQLite, PostgreSQL, and MySQL connections.
"""
import sqlite3
import os
from typing import Dict, Any

def connect_sqlite(db_path: str) -> sqlite3.Connection:
    """Connect to a SQLite database."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_db_connection(db_type: str = "sqlite", config: Dict[str, Any] = None) -> Any:
    """Get database connection based on type."""
    config = config or {}
    if db_type == "sqlite":
        return connect_sqlite(config.get("db_path", "data.db"))
    elif db_type == "postgresql":
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                database=config.get("database", "postgres"),
                user=config.get("user", "postgres"),
                password=config.get("password", "")
            )
            return conn
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL connections")
    elif db_type == "mysql":
        try:
            import pymysql
            conn = pymysql.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                database=config.get("database", "mysql"),
                user=config.get("user", "root"),
                password=config.get("password", "")
            )
            return conn
        except ImportError:
            raise ImportError("pymysql is required for MySQL connections")
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def get_tables(conn) -> list:
    """Get all table names from the database."""
    if isinstance(conn, sqlite3.Connection):
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
    else:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        return [row[0] for row in cursor.fetchall()]

def get_table_schema(conn, table_name: str) -> list:
    """Get schema information for a specific table."""
    if isinstance(conn, sqlite3.Connection):
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        return [{"column": row[1], "type": row[2], "nullable": not row[3], "default": row[4]} for row in cursor.fetchall()]
    else:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """)
        return [{"column": row[0], "type": row[1], "nullable": row[2] == "YES", "default": row[3]} for row in cursor.fetchall()]

if __name__ == "__main__":
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = connect_sqlite(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    print("Tables:", get_tables(conn))
    print("Schema:", get_table_schema(conn, "test"))
    conn.close()
    os.unlink(db_path)
    print("Database connection utility ready!")
