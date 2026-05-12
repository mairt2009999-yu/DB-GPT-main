"""RLS SQL audit persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, desc

from dbgpt.storage.metadata import BaseDao, Model


@dataclass
class RLSAuditRecord:
    conv_id: str
    source: str = "unknown"
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    sys_code: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    datasource: Optional[str] = None
    db_type: Optional[str] = None
    rls_mode: str = "off"
    fail_strategy: str = "close"
    original_sql: Optional[str] = None
    rewritten_sql: Optional[str] = None
    executed_sql: Optional[str] = None
    rls_snapshot: Dict[str, str] = field(default_factory=dict)
    status: str = "success"
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    row_count: Optional[int] = None
    duration_ms: Optional[int] = None
    request_id: Optional[str] = None


class RLSAuditEntity(Model):
    __tablename__ = "rls_sql_audit"
    __table_args__ = (
        Index("idx_rls_audit_conv_created", "conv_id", "created_at"),
        Index("idx_rls_audit_user_created", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="audit id")
    conv_id = Column(String(255), nullable=False, index=True, comment="conversation id")
    source = Column(String(128), nullable=False, comment="SQL execution source")
    user_id = Column(String(128), nullable=True, index=True, comment="user id")
    tenant_id = Column(String(128), nullable=True, comment="tenant id")
    sys_code = Column(String(128), nullable=True, index=True, comment="system code")
    roles = Column(Text, nullable=True, comment="principal roles JSON")
    datasource = Column(String(255), nullable=True, comment="datasource name")
    db_type = Column(String(64), nullable=True, comment="datasource db type")
    rls_mode = Column(String(32), nullable=False, comment="off/shadow/enforce")
    fail_strategy = Column(String(32), nullable=False, comment="close/open")
    original_sql = Column(Text, nullable=True, comment="original SQL")
    rewritten_sql = Column(Text, nullable=True, comment="RLS rewritten SQL")
    executed_sql = Column(Text, nullable=True, comment="SQL sent to datasource")
    rls_snapshot = Column(Text, nullable=True, comment="RLS predicate snapshot JSON")
    status = Column(String(32), nullable=False, index=True, comment="success/failed")
    error_type = Column(String(128), nullable=True, comment="error type")
    error_message = Column(Text, nullable=True, comment="error message")
    row_count = Column(Integer, nullable=True, comment="returned row count")
    duration_ms = Column(Integer, nullable=True, comment="execution duration ms")
    request_id = Column(String(128), nullable=True, comment="request id")
    created_at = Column(DateTime, default=datetime.utcnow, comment="created time")


class RLSAuditDao(BaseDao):
    def insert(self, record: RLSAuditRecord) -> int:
        entity = RLSAuditEntity(
            conv_id=record.conv_id,
            source=record.source,
            user_id=record.user_id,
            tenant_id=record.tenant_id,
            sys_code=record.sys_code,
            roles=self._json_dump(record.roles),
            datasource=record.datasource,
            db_type=record.db_type,
            rls_mode=record.rls_mode,
            fail_strategy=record.fail_strategy,
            original_sql=record.original_sql,
            rewritten_sql=record.rewritten_sql,
            executed_sql=record.executed_sql,
            rls_snapshot=self._json_dump(record.rls_snapshot),
            status=record.status,
            error_type=record.error_type,
            error_message=record.error_message,
            row_count=record.row_count,
            duration_ms=record.duration_ms,
            request_id=record.request_id,
        )
        with self.session() as session:
            session.add(entity)
            session.flush()
            return int(entity.id)

    def list_by_conv_id(self, conv_id: str) -> List[RLSAuditEntity]:
        with self.session(commit=False) as session:
            rows = (
                session.query(RLSAuditEntity)
                .filter(RLSAuditEntity.conv_id == conv_id)
                .order_by(desc(RLSAuditEntity.id))
                .all()
            )
            for row in rows:
                session.expunge(row)
            return rows

    def _json_dump(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)
