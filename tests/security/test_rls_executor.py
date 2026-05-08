# tests/security/test_rls_executor.py
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
import pandas as pd

from dbgpt_app.security.rls_executor import RLSAwareSQLExecutor, SQLExecutionResult
from dbgpt_app.security.principal import Principal
from dbgpt_app.security.rls_client import RLSTableRef, RLSRule
from dbgpt_app.security.stub_rls_client import StubRLSClient
from dbgpt_app.security.exceptions import PermissionDeniedError, RLSUpstreamUnavailableError


@pytest.fixture
def datasource():
    ds = MagicMock()
    ds.db_type = "sqlite"
    ds.db_name = "testdb"
    df = pd.DataFrame({"id": [1, 2]})
    ds.run_to_df = MagicMock(return_value=df)
    return ds


@pytest.fixture
def principal():
    return Principal(user_id="alice", roles=("ANALYST",))


def _make_executor(datasource, rls_client, principal, mode="enforce"):
    return RLSAwareSQLExecutor(
        datasource=datasource,
        rls_client=rls_client,
        principal=principal,
        conversation_id="conv1",
        rls_mode=mode,
    )


@pytest.mark.asyncio
async def test_mode_off_bypasses_rls(datasource, principal):
    executor = _make_executor(datasource, StubRLSClient(), principal, mode="off")
    result = await executor.execute("SELECT * FROM orders")
    assert result.rls_mode == "off"
    assert result.rls_snapshot == {}


@pytest.mark.asyncio
async def test_mode_enforce_rewrites_sql(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = 'A'")
    ])
    executor = _make_executor(datasource, mock_client, principal, mode="enforce")
    result = await executor.execute("SELECT id FROM orders")
    assert "region" in result.rewritten_sql
    assert result.rls_mode == "enforce"


@pytest.mark.asyncio
async def test_mode_shadow_executes_original_sql(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=True, predicate="region = 'A'")
    ])
    executor = _make_executor(datasource, mock_client, principal, mode="shadow")
    result = await executor.execute("SELECT id FROM orders")
    # Shadow mode: executed_sql is original, but rewritten_sql is computed
    assert result.rls_mode == "shadow"
    assert "region" in result.rewritten_sql
    assert datasource.run_to_df.called
    # Should have called with ORIGINAL sql
    called_sql = datasource.run_to_df.call_args[0][0]
    assert "region" not in called_sql  # original sql, no predicate injected


@pytest.mark.asyncio
async def test_permission_denied_raises(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(return_value=[
        RLSRule(table="orders", allowed=False, predicate="")
    ])
    executor = _make_executor(datasource, mock_client, principal, mode="enforce")
    with pytest.raises(PermissionDeniedError):
        await executor.execute("SELECT id FROM orders")


@pytest.mark.asyncio
async def test_upstream_unavailable_fail_close(datasource, principal):
    mock_client = AsyncMock()
    mock_client.batch_fetch = AsyncMock(side_effect=RLSUpstreamUnavailableError("down"))
    executor = _make_executor(datasource, mock_client, principal, mode="enforce")
    with pytest.raises(RLSUpstreamUnavailableError):
        await executor.execute("SELECT id FROM orders")


@pytest.mark.asyncio
async def test_result_contains_data_and_metadata(datasource, principal):
    executor = _make_executor(datasource, StubRLSClient(), principal, mode="off")
    result = await executor.execute("SELECT * FROM orders")
    assert isinstance(result, SQLExecutionResult)
    assert result.data is not None
    assert isinstance(result.rls_snapshot, dict)
