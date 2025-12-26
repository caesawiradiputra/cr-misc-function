from app.connections.strategies import create_strategy


def main():
    mssql_connector = create_strategy("mssql")

    with mssql_connector as mssql:
        mssql.execute_query("SELECT 1 AS test_col")
