"""Tests for dbgpt_app.security.principal."""

from __future__ import annotations

from dbgpt_app.microservice.context import (
    RequestContext,
    reset_current_request_context,
    set_current_request_context,
)
from dbgpt_app.security.principal import (
    Principal,
    current_principal,
    from_chat_param,
    is_admin,
)


class _FakeChatParam:
    """Minimal stand-in for ChatParam to avoid heavy imports during tests."""

    def __init__(self, user_name: str = "", sys_code: str | None = None):
        self.user_name = user_name
        self.sys_code = sys_code


def test_principal_alias_is_request_context():
    assert Principal is RequestContext


def test_is_admin_false():
    p = Principal(user_id="alice", roles=["ANALYST"])
    assert not is_admin(p)


def test_is_admin_true():
    p = Principal(user_id="admin", roles=["ROLE_DBGPT_ADMIN", "ANALYST"])
    assert is_admin(p)


def test_from_chat_param_user_name():
    cp = _FakeChatParam(user_name="bob", sys_code="tenant1")
    p = from_chat_param(cp)
    assert p.user_id == "bob"
    assert p.sys_code == "tenant1"


def test_from_chat_param_empty_falls_back_to_anonymous():
    cp = _FakeChatParam(user_name="", sys_code=None)
    p = from_chat_param(cp)
    assert p.user_id == "anonymous"
    assert p.sys_code is None


def test_current_principal_uses_contextvar():
    ctx = RequestContext(user_id="alice", sys_code="corp", roles=["ANALYST"])
    token = set_current_request_context(ctx)
    try:
        p = current_principal()
        assert p.user_id == "alice"
        assert p.sys_code == "corp"
    finally:
        reset_current_request_context(token)


def test_current_principal_fallback_to_chat_param():
    # contextvar default is None → no user_id → fall back to chat_param
    cp = _FakeChatParam(user_name="bob", sys_code="tenant1")
    p = current_principal(chat_param=cp)
    assert p.user_id == "bob"
    assert p.sys_code == "tenant1"


def test_current_principal_no_context_no_chat_param_returns_anonymous():
    p = current_principal()
    assert p.user_id == "anonymous"
