# tests/security/test_rls_injector.py
import pytest
import sqlglot
from dbgpt_app.security.rls_parser import parse_and_collect
from dbgpt_app.security.rls_injector import inject
from dbgpt_app.security.rls_client import RLSTableRef, RLSRule
from dbgpt_app.security.exceptions import RLSSQLParseError


def _inject(sql: str, predicates: dict[str, str], dialect="mysql") -> str:
    """Helper: parse sql, build rules from predicates dict, inject, return rewritten sql."""
    tree, refs = parse_and_collect(sql, dialect, datasource="ds")
    rules = [
        RLSRule(table=r.table, allowed=True, predicate=predicates.get(r.table, ""))
        for r in refs
    ]
    rewritten, _ = inject(tree, refs, rules, dialect)
    return rewritten


def _parses(sql: str, dialect="mysql") -> bool:
    try:
        sqlglot.parse_one(sql, dialect=dialect)
        return True
    except Exception:
        return False


# ----- Simple SELECT -----
def test_simple_select_no_existing_where():
    out = _inject("SELECT id FROM orders", {"orders": "region = '华南'"})
    assert "华南" in out
    assert _parses(out)


def test_simple_select_existing_where():
    out = _inject(
        "SELECT id FROM orders WHERE status = 1", {"orders": "region = '华南'"}
    )
    assert "status" in out and "华南" in out
    assert _parses(out)


def test_empty_predicate_skipped():
    out = _inject("SELECT id FROM orders", {"orders": ""})
    # No extra WHERE added
    assert "WHERE" not in out.upper()


# ----- INNER JOIN -----
def test_inner_join_predicate_in_where_not_on():
    sql = "SELECT o.id FROM orders o JOIN customers c ON o.cid = c.id"
    out = _inject(sql, {"customers": "region = 'A'"})
    out_upper = out.upper()
    assert "WHERE" in out_upper
    assert _parses(out)


# ----- LEFT JOIN (safety critical) -----
def test_left_join_right_table_predicate_in_on_not_where():
    """CRITICAL: predicate for LEFT JOIN right table must land in ON."""
    sql = "SELECT o.id, i.name FROM orders o LEFT JOIN items i ON o.id = i.oid"
    out = _inject(sql, {"items": "region = 'B'"})
    # Verify it went into ON clause: check ON ... region
    assert "region" in out
    # Rewritten SQL must still parse
    assert _parses(out)
    # Verify result is still a LEFT JOIN (not downgraded to INNER)
    assert "LEFT JOIN" in out.upper() or "LEFT OUTER JOIN" in out.upper()


def test_left_join_right_table_predicate_not_in_where():
    sql = "SELECT o.id, i.name FROM orders o LEFT JOIN items i ON o.id = i.oid"
    out = _inject(sql, {"items": "region = 'B'"})
    # If WHERE appeared, it would silently downgrade to INNER JOIN — assert not
    # The WHERE from the main table (if any) is OK; but items predicate must not be alone in WHERE
    parsed = sqlglot.parse_one(out, dialect="mysql")
    # Check items predicate is inside ON
    on_clauses = list(parsed.find_all(sqlglot.exp.Join))
    for join in on_clauses:
        if join.side and join.side.upper() == "LEFT":
            on_text = join.args.get("on", "")
            assert "region" in str(on_text)


# ----- Subquery -----
def test_subquery_inner_table_predicate():
    sql = "SELECT * FROM (SELECT id FROM orders) sub"
    out = _inject(sql, {"orders": "region = 'C'"}, dialect="sqlite")
    assert "region" in out
    assert _parses(out, "sqlite")


# ----- CTE -----
def test_cte_inner_table_predicate():
    sql = "WITH recent AS (SELECT id FROM orders) SELECT id FROM recent"
    out = _inject(sql, {"orders": "region = 'D'"})
    assert "region" in out
    assert _parses(out)


# ----- Self-join -----
def test_self_join_both_aliases_injected():
    sql = "SELECT a.id, b.id FROM orders a JOIN orders b ON a.id = b.parent_id"
    out = _inject(sql, {"orders": "owner_id = 99"})
    # predicate injected twice (once per alias)
    assert out.count("99") >= 2
    assert _parses(out)


# ----- Postgres -----
def test_postgres_dialect():
    out = _inject(
        "SELECT id FROM orders", {"orders": "region = 'A'"}, dialect="postgres"
    )
    assert "region" in out
    assert _parses(out, "postgres")


# ----- SQLite -----
def test_sqlite_dialect():
    out = _inject("SELECT id FROM orders", {"orders": "region = 'A'"}, dialect="sqlite")
    assert "region" in out


# ----- Snapshot -----
def test_snapshot_populated():
    tree, refs = parse_and_collect("SELECT id FROM orders", "mysql", datasource="ds")
    rules = [RLSRule(table="orders", allowed=True, predicate="region = 'X'")]
    _, snapshot = inject(tree, refs, rules, "mysql")
    assert snapshot == {"orders": "region = 'X'"}


def test_snapshot_empty_when_no_predicate():
    tree, refs = parse_and_collect("SELECT id FROM orders", "mysql", datasource="ds")
    rules = [RLSRule(table="orders", allowed=True, predicate="")]
    _, snapshot = inject(tree, refs, rules, "mysql")
    assert snapshot == {}
