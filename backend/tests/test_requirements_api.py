from app.seed import REQUIREMENT_MAPPINGS


def test_requirement_endpoint_contains_every_shimo_item(client):
    rows = client.get("/api/requirements").json()
    ids = {row["id"] for row in rows}

    assert ids == {row[0] for row in REQUIREMENT_MAPPINGS}
    assert len(rows) == 15
    assert all(row["page"] and row["acceptance"] for row in rows)


def test_requirement_endpoint_filters_module_and_priority(client):
    rows = client.get(
        "/api/requirements", params={"module": "知识库管理", "priority": "P0"}
    ).json()

    assert {row["id"] for row in rows} == {"3.2", "3.3"}
    assert all(row["module"] == "知识库管理" and row["priority"] == "P0" for row in rows)
