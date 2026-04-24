#!/usr/bin/env python3
"""SQL Query execution and analysis utility."""
import json
import pandas as pd
import sqlite3
from typing import Dict, Any, List

def execute_query(conn, query: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame."""
    if isinstance(conn, sqlite3.Connection):
        return pd.read_sql_query(query, conn)
    else:
        return pd.read_sql_query(query, conn)

def get_query_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate summary statistics for query results."""
    summary = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
        "numeric_summary": {},
        "categorical_summary": {}
    }
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            summary["numeric_summary"][col] = {
                "min": float(df[col].min()) if pd.notna(df[col].min()) else None,
                "max": float(df[col].max()) if pd.notna(df[col].max()) else None,
                "mean": float(df[col].mean()) if pd.notna(df[col].mean()) else None,
                "median": float(df[col].median()) if pd.notna(df[col].median()) else None,
                "std": float(df[col].std()) if pd.notna(df[col].std()) else None
            }
        elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
            value_counts = df[col].value_counts().head(10).to_dict()
            summary["categorical_summary"][col] = {
                "unique_values": int(df[col].nunique()),
                "top_values": {str(k): int(v) for k, v in value_counts.items()}
            }
    return summary

def analyze_sql_patterns(queries: List[str]) -> Dict[str, Any]:
    """Analyze SQL query patterns and complexity."""
    analysis = {
        "total_queries": len(queries),
        "query_types": {"SELECT": 0, "INSERT": 0, "UPDATE": 0, "DELETE": 0, "CREATE": 0, "ALTER": 0, "DROP": 0},
        "complexity": [],
        "tables_used": set(),
        "has_joins": 0,
        "has_subqueries": 0,
        "has_aggregations": 0
    }
    for query in queries:
        upper_query = query.upper().strip()
        for qtype in analysis["query_types"]:
            if upper_query.startswith(qtype):
                analysis["query_types"][qtype] += 1
                break
        complexity = "simple"
        if "JOIN" in upper_query:
            analysis["has_joins"] += 1
            complexity = "medium"
        if "SELECT" in upper_query and "(" in query and "SELECT" in query[query.find("("):]:
            analysis["has_subqueries"] += 1
            complexity = "complex"
        if any(agg in upper_query for agg in ["GROUP BY", "HAVING", "SUM(", "COUNT(", "AVG(", "MAX(", "MIN("]):
            analysis["has_aggregations"] += 1
            if complexity == "simple":
                complexity = "medium"
        analysis["complexity"].append(complexity)
    analysis["tables_used"] = list(analysis["tables_used"])
    return analysis

if __name__ == "__main__":
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sales (id INTEGER, product TEXT, amount REAL, date TEXT)")
    conn.execute("INSERT INTO sales VALUES (1, 'Widget', 100.0, '2024-01-01')")
    conn.execute("INSERT INTO sales VALUES (2, 'Gadget', 200.0, '2024-01-02')")
    conn.commit()
    df = execute_query(conn, "SELECT * FROM sales")
    print("Query Results:")
    print(df)
    print("\nSummary:")
    print(json.dumps(get_query_summary(df), indent=2))
    conn.close()
    os.unlink(db_path)
    print("\nQuery execution utility ready!")
