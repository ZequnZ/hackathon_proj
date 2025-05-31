import psycopg2
from psycopg2 import OperationalError

# from sqlalchemy import create_engine
# import pandas as pd
# from typing import Optional

# NOTE: Install psycopg2 if not already installed: pip install psycopg2


def get_db_connection(
    user: str,
    password: str,
    dbname: str,
    host: str,
    port: int,
):
    """
    Establish a connection to the PostgreSQL database running in a container named 'db'.
    Returns a connection object. Raises OperationalError on failure.
    """
    try:
        conn = psycopg2.connect(
            dbname=dbname, user=user, password=password, host=host, port=port
        )
        return conn
    except OperationalError as e:
        print(f"Error connecting to the database: {e}")
        raise


def run_query(
    conn,
    query: str,
    params: tuple = (),
) -> list[tuple]:
    """
    Run a SQL query on the PostgreSQL database. Returns the result as a list of tuples.
    If the query is not a SELECT, returns an empty list.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:  # SELECT queries
                result = cur.fetchall()
            else:
                result = []
            conn.commit()
            return result
    except Exception as e:
        print(f"Error running query: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


# def get_sqlalchemy_engine(
#     user: str,
#     password: str,
#     dbname: str,
#     host: str,
#     port: int,
# ):
#     """
#     Create and return a SQLAlchemy engine for the PostgreSQL database.
#     """
#     engine_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
#     return create_engine(engine_url)


# def run_query_sqlalchemy(
#     engine,
#     query: str,
#     params: Optional[dict] = None,
# ) -> pd.DataFrame:
#     """
#     Run a SQL query using SQLAlchemy and return the result as a pandas DataFrame.
#     Example usage:
#         engine = get_sqlalchemy_engine(...)
#         df = run_query_sqlalchemy(
#             engine,
#             query="SELECT * FROM us_states WHERE id = %(id)s",
#             params={"id": 1},
#         )
#     """
#     with engine.connect() as connection:
#         df = pd.read_sql_query(query, connection, params=params)
#     return df


def get_table_names(conn):
    """
    Get a list of table names in the PostgreSQL database.
    """
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
    return run_query(conn, query)


if __name__ == "__main__":
    # Example usage (remove or comment out in production):
    conn = get_db_connection(
        user="user",
        password="password",
        dbname="northwind",
        host="0.0.0.0",
        port=5432,
    )

    results = run_query(conn, "select * from us_states", (1,))
    # results = get_table_names(conn)
    print(results)
