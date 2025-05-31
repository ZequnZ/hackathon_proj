import psycopg2
from psycopg2 import OperationalError

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


# Example usage (remove or comment out in production):
conn = get_db_connection(
    user="postgres",
    password="postgres",
    dbname="northwind",
    host="localhost",
    port=55432,
)


if __name__ == "__main__":
    results = run_query(conn, "select * from us_states", (1,))
    print(results)
