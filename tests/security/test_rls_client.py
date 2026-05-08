# tests/security/test_rls_client.py
import pytest
from unittest.mock import AsyncMock
from dbgpt_app.microservice.context import RequestContext
from dbgpt_app.microservice.user_service import (
    SqlFragment,
    AuthorizationFailedError,
    ServiceUnavailableError,
)
from dbgpt_app.security.rls_client import RLSClient, RLSTableRef, RLSRule
from dbgpt_app.security.exceptions import RLSUpstreamUnavailableError


@pytest.fixture
def principal():
    return RequestContext(user_id="alice", sys_code="corp", roles=["ANALYST"])


@pytest.fixture
def tables():
    return [RLSTableRef(datasource="ds", schema="sales", table="orders", alias="orders")]


@pytest.mark.asyncio
async def test_batch_fetch_calls_user_service(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        return_value=SqlFragment(user_id="alice", table_code="orders", sql_fragment='create_by="1"')
    )
    client = RLSClient(user_service=mock_user_svc, local_ttl_seconds=60)
    rules = await client.batch_fetch(principal, tables)
    assert len(rules) == 1
    assert rules[0].allowed is True
    assert rules[0].predicate == 'create_by="1"'
    mock_user_svc.get_sql_fragment_by_user_id.assert_awaited_once_with(principal, "orders")


@pytest.mark.asyncio
async def test_batch_fetch_empty_fragment_means_allowed(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        return_value=SqlFragment(user_id="alice", table_code="orders", sql_fragment="")
    )
    client = RLSClient(user_service=mock_user_svc)
    rules = await client.batch_fetch(principal, tables)
    assert rules[0].allowed is True
    assert rules[0].predicate == ""


@pytest.mark.asyncio
async def test_batch_fetch_authorization_failed_means_denied(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=AuthorizationFailedError("forbidden")
    )
    client = RLSClient(user_service=mock_user_svc)
    rules = await client.batch_fetch(principal, tables)
    assert rules[0].allowed is False


@pytest.mark.asyncio
async def test_batch_fetch_service_unavailable_raises(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=ServiceUnavailableError("down")
    )
    client = RLSClient(user_service=mock_user_svc)
    with pytest.raises(RLSUpstreamUnavailableError):
        await client.batch_fetch(principal, tables)


@pytest.mark.asyncio
async def test_batch_fetch_l1_cache_hit(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        return_value=SqlFragment(user_id="alice", table_code="orders", sql_fragment='create_by="1"')
    )
    client = RLSClient(user_service=mock_user_svc, local_ttl_seconds=60)
    await client.batch_fetch(principal, tables)
    await client.batch_fetch(principal, tables)
    assert mock_user_svc.get_sql_fragment_by_user_id.await_count == 1


@pytest.mark.asyncio
async def test_batch_fetch_stale_fallback_on_failure(principal, tables):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=[
            SqlFragment(user_id="alice", table_code="orders", sql_fragment='create_by="1"'),
            ServiceUnavailableError("down"),
        ]
    )
    client = RLSClient(
        user_service=mock_user_svc, local_ttl_seconds=0, stale_fallback_seconds=3600
    )
    await client.batch_fetch(principal, tables)
    client._l1_cache.clear()  # force L1 expiry
    rules = await client.batch_fetch(principal, tables)
    assert rules[0].allowed is True
    assert rules[0].predicate == 'create_by="1"'


@pytest.mark.asyncio
async def test_batch_fetch_two_tables_two_calls(principal):
    mock_user_svc = AsyncMock()
    mock_user_svc.get_sql_fragment_by_user_id = AsyncMock(
        side_effect=[
            SqlFragment(user_id="alice", table_code="orders", sql_fragment="a=1"),
            SqlFragment(user_id="alice", table_code="customers", sql_fragment="b=2"),
        ]
    )
    client = RLSClient(user_service=mock_user_svc)
    refs = [
        RLSTableRef(datasource="ds", schema="s", table="orders", alias="o"),
        RLSTableRef(datasource="ds", schema="s", table="customers", alias="c"),
    ]
    rules = await client.batch_fetch(principal, refs)
    assert [r.predicate for r in rules] == ["a=1", "b=2"]
    assert mock_user_svc.get_sql_fragment_by_user_id.await_count == 2


def test_make_cache_key_contains_user_and_table(principal, tables):
    client = RLSClient(user_service=AsyncMock())
    key = client._make_cache_key(principal, tables[0])
    assert "alice" in key
    assert "orders" in key
