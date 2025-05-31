import os

from langchain_community.utilities.sql_database import SQLDatabase
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, inspect, text

from backend.utils.tool_creation import create_tool, registry

if os.getenv("ENVIRONMENT") == "local":
    DATABASE_URL = "postgresql://user:password@db:5432/northwind"
else:
    DATABASE_URL = "postgresql://user:password@0.0.0.0:5432/northwind"

# Database setup (adjust as needed)
engine = create_engine(DATABASE_URL)
db = SQLDatabase(engine=engine)


# Pydantic model for parameters
class SQLDBQueryParams(BaseModel):
    query: str = Field(..., description="A detailed and correct SQL query.")
    reasoning: str = Field(
        ...,
        description="The reasoning process of the query, explain your thought process.",
    )


# Tool function implementation
@create_tool(
    name="sql_db_query",
    description="Input to this tool is a detailed and correct SQL query, output is a result from the database. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query, check the query, and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.",
    parameters_model=SQLDBQueryParams,
)
def sql_db_query(query: str, reasoning: str) -> str:
    """
    Input to this tool is a detailed and correct SQL query, output is a result from the database. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query, check the query, and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
        return f"Reasoning: {reasoning}\n\nResult: {result.fetchall()}"
    except Exception as e:
        return f"Error: {e}"


# Pydantic model for parameters
class SQLDBSchemaParams(BaseModel):
    table_names: str = Field(..., description="A comma-separated list of table names.")


# Tool function implementation
@create_tool(
    name="sql_db_schema",
    description="Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables. Be sure that the tables actually exist by calling sql_db_list_tables first! Example Input: table1, table2, table3",
    parameters_model=SQLDBSchemaParams,
)
def sql_db_schema(table_names: str) -> str:
    """
    Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables. Be sure that the tables actually exist by calling sql_db_list_tables first! Example Input: table1, table2, table3
    """
    inspector = inspect(engine)
    requested_tables = [t.strip() for t in table_names.split(",") if t.strip()]
    existing_tables = inspector.get_table_names()
    output = []
    for table in requested_tables:
        if table not in existing_tables:
            output.append(f"Table '{table}' does not exist.")
            continue
        # Get schema
        columns = inspector.get_columns(table)
        schema_str = ", ".join([f"{col['name']} ({col['type']})" for col in columns])
        # Get sample rows
        with engine.connect() as conn:
            sample_rows = conn.execute(
                text(f"SELECT * FROM {table} LIMIT 3")
            ).fetchall()
        output.append(
            f"Table: {table}\nSchema: {schema_str}\nSample rows: {sample_rows}"
        )
    return "\n\n".join(output)


# Pydantic model for parameters
class SQLDBListTablesParams(BaseModel):
    tool_input: str = Field(..., description="Input is an empty string.")


# Tool function implementation
@create_tool(
    name="sql_db_list_tables",
    description="Input is an empty string, output is a comma-separated list of tables in the database.",
    parameters_model=SQLDBListTablesParams,
)
def sql_db_list_tables(tool_input: str) -> str:
    """
    Input is an empty string, output is a comma-separated list of tables in the database.
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return ", ".join(tables)


# Pydantic model for parameters
class SQLDBQueryCheckerParams(BaseModel):
    query: str = Field(..., description="A detailed and correct SQL query.")


# Tool function implementation
@create_tool(
    name="sql_db_query_checker",
    description="Use this tool to double check if your query is correct before executing it. Always use this tool before executing a query with sql_db_query!",
    parameters_model=SQLDBQueryCheckerParams,
)
def sql_db_query_checker(query: str) -> str:
    """
    Use this tool to double check if your query is correct before executing it. Always use this tool before executing a query with sql_db_query!
    """
    try:
        with engine.connect() as connection:
            # Use EXPLAIN to check the query without executing it
            connection.execute(text(f"EXPLAIN {query}"))
        return "Query is valid."
    except Exception as e:
        return f"Query is NOT valid: {e}"


# Register the tools
registry.register(sql_db_query)
registry.register(sql_db_schema)
registry.register(sql_db_list_tables)
registry.register(sql_db_query_checker)
