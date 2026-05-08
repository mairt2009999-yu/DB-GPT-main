"""StubRLSClient — no-op for mode=off."""

from __future__ import annotations

from typing import List

from dbgpt_app.security.rls_client import RLSTableRef, RLSRule


class StubRLSClient:
    """No-op RLS client. Returns allowed=True, predicate='' for all tables."""

    async def batch_fetch(self, principal, refs: List[RLSTableRef]) -> List[RLSRule]:
        return [RLSRule(table=r.table, allowed=True, predicate="") for r in refs]

    def invalidate(self, user_id: str, sys_code: str = "", table: str = None) -> None:
        pass
