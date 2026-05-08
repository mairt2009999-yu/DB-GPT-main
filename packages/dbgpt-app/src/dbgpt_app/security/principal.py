"""Principal 适配层。

复用 ``microservice.context.RequestContext`` 作为事实上的 Principal。
本模块提供：
1. ``Principal`` —— ``RequestContext`` 的类型别名
2. ``from_chat_param`` —— ChatParam 兜底适配（contextvar 没值时使用）
3. ``current_principal`` —— 优先 contextvar，回退到 chat_param

`ContextMiddleware` 已经在请求生命周期内把 RequestContext 注入到 contextvar，
所以正常 HTTP 请求路径下直接使用 ``current_principal()`` 即可。
"""

from __future__ import annotations

from typing import Optional

from dbgpt_app.microservice.context import (
    RequestContext,
    get_current_request_context,
)

# 类型别名：security 子系统对外的"Principal"就是 RequestContext
Principal = RequestContext


_ADMIN_ROLES = frozenset(
    [
        "ROLE_DBGPT_ADMIN",
        "ROLE_ADMIN",
    ]
)


def is_admin(principal: RequestContext) -> bool:
    """判断 principal 是否带有管理员角色。"""
    return any(r in _ADMIN_ROLES for r in (principal.roles or []))


def from_chat_param(chat_param) -> RequestContext:
    """ChatParam 兜底适配（无 contextvar 时使用，如本地脚本/测试）。"""
    user_id = (getattr(chat_param, "user_name", "") or "").strip() or "anonymous"
    sys_code = getattr(chat_param, "sys_code", None) or None
    return RequestContext(user_id=user_id, sys_code=sys_code, roles=[])


def current_principal(chat_param: Optional[object] = None) -> RequestContext:
    """获取当前请求的 Principal。

    优先级：
      1. contextvar 中已有 RequestContext 且 user_id 非空 → 直接返回
      2. 否则若提供了 chat_param → 用 ``from_chat_param`` 兜底
      3. 否则返回匿名 RequestContext
    """
    ctx = get_current_request_context()
    if ctx and ctx.user_id:
        return ctx
    if chat_param is not None:
        return from_chat_param(chat_param)
    return RequestContext(user_id="anonymous", roles=[])
