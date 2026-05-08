"""Shared fixtures for tests/security/."""

from __future__ import annotations

import pytest

from dbgpt_app.microservice.context import RequestContext
from dbgpt_app.security.principal import Principal


@pytest.fixture
def alice() -> Principal:
    return Principal(user_id="alice", roles=["ANALYST"], sys_code="corp")


@pytest.fixture
def admin() -> Principal:
    return Principal(user_id="admin", roles=["ROLE_DBGPT_ADMIN"], sys_code="corp")


@pytest.fixture
def empty_request_context() -> RequestContext:
    return RequestContext()
