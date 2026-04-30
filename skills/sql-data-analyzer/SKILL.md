---
name: sql-data-analyzer
description: Analyze SQL databases, execute queries, and generate comprehensive HTML reports with insights.
version: 1.0.0
author: System
skill_type: data_analysis
tags: ["sql", "database", "analysis"]
---
# SQL Data Analyzer Skill

## Description
Analyze SQL databases, execute queries, and generate comprehensive HTML reports with insights.

## Core Workflow

### Step 1: Understand User Requirements
- Identify the database type (SQLite, PostgreSQL, MySQL)
- Understand what the user wants to analyze
- Determine if specific tables or custom queries are needed

### Step 2: Connect to Database
- Use `connect_db.py` to establish a database connection
- Parameters: db_type (sqlite/postgresql/mysql), config dict
- For SQLite: requires db_path
- For PostgreSQL: requires host, port, database, user, password
- For MySQL: requires host, port, database, user, password

### Step 3: Explore Database Schema
- Use `get_tables()` to list all tables
- Use `get_table_schema()` to get column info for each table
- Present schema to user for query selection

### Step 4: Execute Queries
- Use `execute_query.py` to run SQL queries
- Use `get_query_summary()` to get statistical summaries
- Support for SELECT, JOIN, GROUP BY, aggregations, etc.

### Step 5: Generate Report
- Use `generate_report.py` to create HTML report
- Includes schema info, query results, statistics, and insights
- Save to file and render via html_interpreter

## Scripts
- `connect_db.py`: Database connection utilities
- `execute_query.py`: SQL execution and analysis
- `generate_report.py`: HTML report generation

## References
- `references/api_reference.md`: API documentation

## Notes
- Always use html_interpreter for final report display
- Support SQLite, PostgreSQL, and MySQL databases
