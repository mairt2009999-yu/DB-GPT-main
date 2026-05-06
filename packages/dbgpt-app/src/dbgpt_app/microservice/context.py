from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from fastapi import HTTPException

_REQUEST_CONTEXT_VAR: ContextVar["RequestContext"] = ContextVar(
    "dbgpt_request_context",
    default=None,
)
_RESOLVED_PRINCIPAL_VAR: ContextVar["ResolvedPrincipal"] = ContextVar(
    "dbgpt_resolved_principal",
    default=None,
)

if TYPE_CHECKING:
    from dbgpt_app.microservice.user_service import ResolvedPrincipal


@dataclass
class RequestContext:
    authorization: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    sys_code: Optional[str] = None


@dataclass
class Principal:
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    sys_code: Optional[str] = None


def set_current_request_context(request_context: RequestContext):
    return _REQUEST_CONTEXT_VAR.set(request_context)


def reset_current_request_context(token) -> None:
    _REQUEST_CONTEXT_VAR.reset(token)


def get_current_request_context() -> RequestContext:
    request_context = _REQUEST_CONTEXT_VAR.get()
    if request_context is None:
        return RequestContext()
    return request_context


def get_current_principal() -> Principal:
    request_context = get_current_request_context()
    return Principal(
        user_id=request_context.user_id,
        tenant_id=request_context.tenant_id,
        roles=list(request_context.roles),
        sys_code=request_context.sys_code,
    )


def set_current_resolved_principal(resolved_principal: "ResolvedPrincipal"):
    return _RESOLVED_PRINCIPAL_VAR.set(resolved_principal)


def reset_current_resolved_principal(token) -> None:
    _RESOLVED_PRINCIPAL_VAR.reset(token)


def get_current_resolved_principal() -> Optional["ResolvedPrincipal"]:
    return _RESOLVED_PRINCIPAL_VAR.get()


def require_authenticated_principal() -> Principal:
    principal = get_current_principal()
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="Missing authenticated principal")
    return principal
