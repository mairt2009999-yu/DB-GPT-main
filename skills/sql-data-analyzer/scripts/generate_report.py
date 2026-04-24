#!/usr/bin/env python3
"""Generate HTML report for SQL data analysis results."""
import json
import os
from typing import Dict, Any, Optional

def generate_html_report(
    schema_info: Dict[str, Any],
    query_results: Dict[str, Any],
    insights: Optional[Dict[str, Any]] = None,
    title: str = "SQL Data Analysis Report"
) -> str:
    """Generate a comprehensive HTML report."""
    insights = insights or {}
    
    # Build tables section
    tables_html = ""
    for table_name, info in schema_info.get("tables", {}).items():
        columns_html = "".join([
            f"<tr><td>{col['column']}</td><td>{col['type']}</td><td>{'Yes' if col['nullable'] else 'No'}</td><td>{col.get('default', 'None')}</td></tr>"
            for col in info.get("columns", [])
        ])
        tables_html += f"""
        <div class="table-section">
            <h3>Table: {table_name}</h3>
            <p>Row count: {info.get('row_count', 'N/A')}</p>
            <table>
                <tr><th>Column</th><th>Type</th><th>Nullable</th><th>Default</th></tr>
                {columns_html}
            </table>
        </div>
        """
    
    # Build query results section
    queries_html = ""
    for qname, qdata in query_results.items():
        if "error" in qdata:
            queries_html += f"""
            <div class="query-section error">
                <h3>Query: {qname}</h3>
                <pre class="sql">{qdata.get('query', '')}</pre>
                <div class="error-msg">Error: {qdata['error']}</div>
            </div>
            """
            continue
        
        summary = qdata.get("summary", {})
        # Build data table
        data_rows = ""
        for row in qdata.get("data", [])[:20]:
            data_rows += "<tr>" + "".join([f"<td>{v}</td>" for v in row]) + "</tr>"
        
        columns = summary.get("columns", [])
        header_row = "".join([f"<th>{c}</th>" for c in columns])
        
        # Build numeric summary
        num_summary_html = ""
        for col, stats in summary.get("numeric_summary", {}).items():
            num_summary_html += f"""
            <div class="stat-card">
                <h4>{col}</h4>
                <p>Min: {stats.get('min', 'N/A')}</p>
                <p>Max: {stats.get('max', 'N/A')}</p>
                <p>Mean: {stats.get('mean', 'N/A')}</p>
                <p>Median: {stats.get('median', 'N/A')}</p>
                <p>Std: {stats.get('std', 'N/A')}</p>
            </div>
            """
        
        queries_html += f"""
        <div class="query-section">
            <h3>Query: {qname}</h3>
            <pre class="sql">{qdata.get('query', '')}</pre>
            <p>Rows: {summary.get('row_count', 0)} | Columns: {summary.get('column_count', 0)}</p>
            
            <h4>Statistical Summary</h4>
            <div class="stats-container">{num_summary_html}</div>
            
            <h4>Data Preview (first 20 rows)</h4>
            <div class="table-wrapper">
                <table>
                    <tr>{header_row}</tr>
                    {data_rows}
                </table>
            </div>
        </div>
        """
    
    # Build insights section
    insights_html = ""
    if insights:
        for category, items in insights.items():
            items_html = "".join([f"<li>{item}</li>" for item in (items if isinstance(items, list) else [items])])
            insights_html += f"""
            <div class="insight-section">
                <h3>{category.replace('_', ' ').title()}</h3>
                <ul>{items_html}</ul>
            </div>
            """
    
    # Build complete HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 30px; }}
        h2 {{ color: #2c3e50; margin: 25px 0 15px; }}
        h3 {{ color: #34495e; margin: 20px 0 10px; }}
        h4 {{ color: #555; margin: 10px 0 5px; }}
        .table-section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .query-section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .query-section.error {{ border-left: 4px solid #e74c3c; }}
        .insight-section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
        tr:hover {{ background: #f5f5f5; }}
        pre.sql {{ background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; overflow-x: auto; font-family: 'Fira Code', monospace; margin: 10px 0; }}
        .stats-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin: 15px 0; }}
        .stat-card {{ background: #f8f9fa; border-radius: 6px; padding: 15px; border: 1px solid #e0e0e0; }}
        .stat-card h4 {{ color: #3498db; margin-bottom: 8px; }}
        .stat-card p {{ margin: 3px 0; font-size: 14px; }}
        .error-msg {{ color: #e74c3c; padding: 10px; background: #fdf0ef; border-radius: 4px; margin: 10px 0; }}
        .table-wrapper {{ overflow-x: auto; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 20px; text-align: center; }}
        .summary-card h3 {{ color: white; font-size: 28px; }}
        .summary-card p {{ color: rgba(255,255,255,0.9); font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <h2>Database Schema</h2>
        {tables_html}
        
        <h2>Query Results & Analysis</h2>
        {queries_html}
        
        <h2>Insights</h2>
        {insights_html}
        
        <div style="text-align: center; margin-top: 40px; color: #888; font-size: 12px;">
            <p>Generated by SQL Data Analyzer | DB-GPT</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html

def save_report(html: str, output_path: str = "sql_analysis_report.html"):
    """Save HTML report to file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report saved to {output_path}")
    return output_path

if __name__ == "__main__":
    # Test with sample data
    schema_info = {
        "tables": {
            "sales": {
                "columns": [
                    {"column": "id", "type": "INTEGER", "nullable": False, "default": None},
                    {"column": "product", "type": "TEXT", "nullable": True, "default": None},
                    {"column": "amount", "type": "REAL", "nullable": True, "default": None},
                    {"column": "date", "type": "TEXT", "nullable": True, "default": None}
                ],
                "row_count": 100
            }
        }
    }
    query_results = {
        "Total Sales by Product": {
            "query": "SELECT product, SUM(amount) as total FROM sales GROUP BY product",
            "summary": {
                "row_count": 5,
                "column_count": 2,
                "columns": ["product", "total"],
                "numeric_summary": {
                    "total": {"min": 100.0, "max": 500.0, "mean": 300.0, "median": 300.0, "std": 141.4}
                }
            },
            "data": [["Widget", 500.0], ["Gadget", 300.0], ["Doohickey", 200.0]]
        }
    }
    insights = {
        "Key Findings": ["Total sales across all products: $1000", "Widget is the best-selling product"],
        "Recommendations": ["Consider increasing Widget inventory", "Analyze seasonal trends"]
    }
    
    html = generate_html_report(schema_info, query_results, insights, "Test SQL Report")
    save_report(html, "/tmp/test_report.html")
    print("Report generation utility ready!")
