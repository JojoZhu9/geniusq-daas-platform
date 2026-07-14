import pytest

from app.db import get_engine
from app.services.sql_guard import (
    SqlSafetyError,
    execute_read_only,
    validate_read_only_sql,
)


ALLOWED = {"house_price_monthly", "housing_transactions"}


def test_accepts_single_select_from_allowed_table():
    sql = validate_read_only_sql(
        "SELECT district, avg_price FROM house_price_monthly", ALLOWED
    )
    assert sql.startswith("SELECT")


def test_accepts_with_query_when_base_tables_are_allowed():
    sql = validate_read_only_sql(
        "WITH prices AS ("
        "SELECT district, AVG(avg_price) AS avg_price "
        "FROM house_price_monthly GROUP BY district"
        ") SELECT * FROM prices",
        ALLOWED,
    )

    assert sql.startswith("WITH")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM house_price_monthly",
        "SELECT 1; DROP TABLE house_price_monthly",
        "PRAGMA table_info(house_price_monthly)",
        "SELECT * FROM secret_users",
    ],
)
def test_rejects_unsafe_sql(sql):
    with pytest.raises(SqlSafetyError):
        validate_read_only_sql(sql, ALLOWED)


def test_execute_read_only_returns_mappings_and_enforces_row_limit():
    engine = get_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE metrics (value INTEGER)")
        connection.exec_driver_sql("INSERT INTO metrics VALUES (1), (2), (3)")

    rows = execute_read_only(engine, "SELECT value FROM metrics ORDER BY value", 2)

    assert rows == [{"value": 1}, {"value": 2}]


def test_execute_read_only_rejects_non_positive_row_limit():
    engine = get_engine("sqlite:///:memory:")

    with pytest.raises(ValueError, match="row_limit"):
        execute_read_only(engine, "SELECT 1 AS value", -1)
