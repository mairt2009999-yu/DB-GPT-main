# tests/security/test_rls_integration.py
"""End-to-end tests using real SQLite + in-process mock RLSClient."""
import asyncio
import sqlite3
import pytest
import pandas as pd
from unittest.mock import AsyncMock

from dbgpt_app.security.rls_executor import RLSAwareSQLExecutor
from dbgpt_app.security.principal import Principal
from dbgpt_app.security.rls_client import RLSRule


@pytest.fixture
def sqlite_ds(tmp_path):
    """Minimal datasource stub backed by a real in-memory SQLite."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE TABLE orders (id INT, region TEXT, amount INT)")
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?)", [
        (1, "华南", 100), (2, "华南", 200),
        (3, "华北", 300), (4, "华北", 400), (5, "华北", 500),
    ])
    conn.commit()

    class FakeDS:
        db_type = "sqlite"
        db_name = "test"

        def run_to_df(self, sql: str) -> pd.DataFrame:
            return pd.read_sql_query(sql, conn)

    return FakeDS()


@pytest.mark.asyncio
async def test_enforce_filters_to_huanan(sqlite_ds):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = '华南'")
    ])
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=mock_client,
        principal=principal, conversation_id="c1", rls_mode="enforce"
    )
    result = await executor.execute("SELECT * FROM orders")
    assert len(result.data) == 2
    assert set(result.data["region"]) == {"华南"}


@pytest.mark.asyncio
async def test_shadow_returns_all_rows(sqlite_ds):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = '华南'")
    ])
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=mock_client,
        principal=principal, conversation_id="c1", rls_mode="shadow"
    )
    result = await executor.execute("SELECT * FROM orders")
    # shadow: original sql executed, all 5 rows returned
    assert len(result.data) == 5
    assert "华南" in result.rewritten_sql


@pytest.mark.asyncio
async def test_off_returns_all_rows(sqlite_ds):
    from dbgpt_app.security.stub_rls_client import StubRLSClient
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=StubRLSClient(),
        principal=principal, conversation_id="c1", rls_mode="off"
    )
    result = await executor.execute("SELECT * FROM orders")
    assert len(result.data) == 5
    assert result.rls_snapshot == {}


@pytest.mark.asyncio
async def test_snapshot_recorded(sqlite_ds):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = '华南'")
    ])
    principal = Principal(user_id="alice")
    executor = RLSAwareSQLExecutor(
        datasource=sqlite_ds, rls_client=mock_client,
        principal=principal, conversation_id="c1", rls_mode="enforce"
    )
    result = await executor.execute("SELECT * FROM orders")
    assert result.rls_snapshot == {"orders": "region = '华南'"}
