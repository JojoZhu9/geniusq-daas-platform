from sqlalchemy import text


def test_datasource_overview_summarizes_business_tables(client):
    response = client.get("/api/datasource/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["database"]["engine"] == "SQLite"
    assert payload["table_count"] >= 4
    assert payload["column_count"] >= 20
    assert payload["row_count"] > 0
    assert "house_price_monthly" in payload["business_tables"]


def test_datasource_tables_hide_internal_runtime_tables(client):
    response = client.get("/api/datasource/tables")

    assert response.status_code == 200
    table_names = [table["name"] for table in response.json()]
    assert "house_price_monthly" in table_names
    assert "analysis_runs" not in table_names
    assert "messages" not in table_names


def test_datasource_table_detail_includes_columns_samples_and_questions(client):
    response = client.get("/api/datasource/tables/house_price_monthly")

    assert response.status_code == 200
    payload = response.json()
    column_names = [column["name"] for column in payload["columns"]]
    assert payload["name"] == "house_price_monthly"
    assert payload["row_count"] > 0
    assert "district" in column_names
    assert "avg_price" in column_names
    assert payload["sample_rows"]
    assert any("平均房价" in question for question in payload["suggested_questions"])


def test_datasource_table_detail_rejects_unknown_or_internal_table(client):
    assert client.get("/api/datasource/tables/not_exist").status_code == 404
    assert client.get("/api/datasource/tables/messages").status_code == 404
