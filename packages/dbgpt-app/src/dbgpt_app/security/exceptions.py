"""RLS 子系统统一异常类。

集中所有 RLS 相关异常的定义，避免在 rls_executor / rls_client 中各自重复定义。
"""


class RLSError(Exception):
    """所有 RLS 相关异常的父类。"""


class PermissionDeniedError(RLSError):
    """用户对 SQL 中某张表无访问权限。

    message 中包含被拒绝的表名，供调用方返回友好错误信息。
    """


class RLSSQLParseError(RLSError):
    """sqlglot 解析失败，或改写后语法校验失败。"""


class RLSUpstreamUnavailableError(RLSError):
    """上游权限服务不可用，且无可用 stale 缓存兜底。"""


class RLSUnsupportedSQLError(RLSError):
    """非 SELECT 语句、不支持的方言等被显式拒绝的情况。"""
