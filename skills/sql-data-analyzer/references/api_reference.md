# SQL Data Analyzer API Reference

## Database Connection

### connect_db(db_type, config)
- **db_type**: str - 'sqlite', 'postgresql', or 'mysql'
- **config**: dict - Connection parameters
  - SQLite: {"db_path": "/path/to/database.db"}
  - PostgreSQL: {"host": "localhost", "port": 5432, "database": "mydb", "user": "user", "password": "pass"}
  - MySQL: {"host": "localhost", "port": 3306, "database": "mydb", "user": "user", "password": "pass"}
- **Returns**: Database connection object

### get_tables(conn)
- **conn**: Database connection
- **Returns**: List of table names

### get_table_schema(conn, table_name)
- **conn**: Database connection
- **table_name**: str - Name of the table
- **Returns**: List of column info dicts with keys: column, type, nullable, default

## Query Execution

### execute_query(conn, query)
- **conn**: Database connection
- **query**: str - SQL query to execute
- **Returns**: pandas DataFrame with query results

### get_query_summary(df)
- **df**: pandas DataFrame
- **Returns**: Dict with row_count, column_count, columns, dtypes, missing_values, numeric_summary, categorical_summary

## Report Generation

### generate_html_report(schema_info, query_results, insights, title)
- **schema_info**: Dict with tables info
- **query_results**: Dict mapping query names to results
- **insights**: Dict with analysis insights
- **title**: str - Report title
- **Returns**: Complete HTML string

### save_report(html, output_path)
- **html**: str - HTML content
- **output_path**: str - File path to save
- **Returns**: Path to saved file
