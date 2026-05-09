"""StubRLSClient — no-op for mode=off."""

from __future__ import annotations

from typing import List

from dbgpt.component import LifeCycle

from dbgpt_app.security.rls_client import RLSRule, RLSTableRef


class StubRLSClient(LifeCycle):
    """No-op RLS client. Returns allowed=True, predicate='' for all tables."""

    name = "dbgpt_stub_rls_client"

    def init_app(self, system_app) -> None:
        self.system_app = system_app

    async def batch_fetch(self, principal, refs: List[RLSTableRef]) -> List[RLSRule]:
        return [RLSRule(table=r.table, allowed=True, predicate="") for r in refs]

    def invalidate(self, user_id: str, sys_code: str = "", table: str = None) -> None:
        pass
