import os
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, inspect, text

from backend.utils.tool_creation import create_tool, registry

if os.getenv("ENVIRONMENT") == "local":
    DATABASE_URL = "postgresql://user:password@db:5432/northwind"
else:
    DATABASE_URL = "postgresql://user:password@0.0.0.0:5432/northwind"

# Database setup (adjust as needed)
engine = create_engine(DATABASE_URL)

VISUALIZATION_TYPES = Literal["bar", "line", "pie", "scatter"]


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
            df = pd.read_sql(query, connection)
        return f"Reasoning: {reasoning}\n\nResults: {df.to_string(max_rows=10)}", df
    except Exception as e:
        return f"Error: {e}", None


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


##############
# Pydantic model for parameters
class SQLDBQueryParams2(BaseModel):
    query: str = Field(..., description="A detailed and correct SQL query.")
    reasoning: str = Field(
        ...,
        description="The reasoning process of the query, explain your thought process.",
    )
    visualization_type: VISUALIZATION_TYPES = Field(
        ...,
        description="The type of visualization to create from the query. Options: bar, line, pie, scatter, etc.",
    )


# Tool function implementation
@create_tool(
    name="sql_db_query2",
    description="Input to this tool is a detailed and correct SQL query, output is a result from the database.The reasoning should include why the visualization type is chosen. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query, check the query, and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.",
    parameters_model=SQLDBQueryParams2,
)
def sql_db_query2(
    query: str, reasoning: str, visualization_type: VISUALIZATION_TYPES
) -> tuple[str, pd.DataFrame | None, VISUALIZATION_TYPES | None]:
    """
    Input to this tool is a detailed and correct SQL query, output is a result from the database. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query, check the query, and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.
    """
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return (
            f"Reasoning: {reasoning}\n\nResults: {df.to_string(max_rows=30)}",
            df,
            visualization_type,
        )
    except Exception as e:
        return f"Error: {e}", None, None


# Pydantic model for parameters
class CreateVisualizationWithPythonCode(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    python_code: str = Field(
        ...,
        description="""Python code to create the visualization based on the data(dataframe) and the visualization type from the graph state.
        Python code should use pandas and seaborn to visualize the given data.
        Only use the top 10 rows of the data to create the visualization.
        Name the dataframe as 'df' and make sure only contains columns that are present in the dataframe.
        Should print any important results or values that need to be shown to the user. SHOULD NOT contain imports, assume that pandas (as pd) and seaborn as (sns) are already imported.
        Output returns its base64-encoded PNG image.
        """,
    )


@create_tool(
    name="create_visualization_with_python_code",
    description="""Input to this tool is the Python code to create the visualization based on the data and the visualization type from the graph state.
    Output is the visualization graph in base64 format.
    Only use the top 5 rows of the data to create the visualization.
    Should print any important results or values that need to be shown to the user. SHOULD NOT contain imports, assume that pandas (as pd) and seaborn as (sns) are already imported.
    Name the dataframe as 'df' in the code.
    """,
    parameters_model=CreateVisualizationWithPythonCode,
)
def create_visualization_with_python_code(python_code: str) -> str:
    """
    Executes the provided Python code (using pandas and seaborn), captures the generated matplotlib plot,
    and returns its base64-encoded PNG image.
    """
    pass


# Register the tools
# registry.register(sql_db_query)
registry.register(sql_db_schema)
registry.register(sql_db_list_tables)
registry.register(sql_db_query_checker)
registry.register(sql_db_query2)
registry.register(create_visualization_with_python_code)
