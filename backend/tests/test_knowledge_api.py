def knowledge_payload(**overrides):
    payload = {
        "name": "测试行政区房价口径",
        "kind": "text",
        "scope": "private",
        "library": "个人知识库",
        "content": "测试口径：平均房价按行政区和月份统计",
        "linked_tables": ["house_price_monthly"],
        "tags": ["房价", "指标口径"],
    }
    payload.update(overrides)
    return payload


def test_same_library_duplicate_is_rejected(client):
    item = knowledge_payload()
    assert client.post("/api/knowledge", json=item).status_code == 201

    duplicate = client.post("/api/knowledge", json=item)

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "KNOWLEDGE_DUPLICATE"
    assert duplicate.json()["existing_id"]


def test_private_item_overrides_public_match(client):
    public = client.post(
        "/api/knowledge",
        json=knowledge_payload(
            name="跨库测试口径",
            scope="public",
            library="公共知识库-测试",
            content="跨库相同内容",
        ),
    ).json()

    result = client.post(
        "/api/knowledge/deduplicate",
        json=knowledge_payload(
            name="跨库测试口径",
            scope="private",
            library="个人知识库-测试",
            content="跨库相同内容",
        ),
    ).json()

    assert result["duplicate"] is False
    assert result["priority"] == "private_over_public"
    assert result["overrides_id"] == public["id"]


def test_sql_knowledge_extracts_links_and_supports_combined_filters(client):
    created = client.post(
        "/api/knowledge",
        json=knowledge_payload(
            name="海淀房价 SQL 模型",
            kind="sql",
            content="SELECT district, avg_price FROM house_price_monthly",
            linked_tables=[],
            tags=["房价", "SQL"],
        ),
    ).json()

    result = client.get("/api/knowledge", params={"query": "海淀", "kind": "sql", "tag": "房价"}).json()

    assert created["linked_tables"] == ["house_price_monthly"]
    assert [item["id"] for item in result] == [created["id"]]


def test_manual_and_scheduled_demo_sync_share_audit_shape(client):
    manual = client.post("/api/sync", json={"mode": "manual"}).json()
    scheduled = client.post("/api/sync", json={"mode": "scheduled_demo"}).json()

    assert manual["status"] == scheduled["status"] == "completed"
    logs = client.get("/api/sync/logs").json()
    assert {row["mode"] for row in logs} >= {"manual", "scheduled_demo"}
    assert all(row["request_id"] for row in logs)


def test_table_delete_requires_confirmation_and_removes_links(client):
    preview = client.delete("/api/data-tables/house_price_monthly")

    assert preview.status_code == 409
    assert preview.json()["code"] == "TABLE_DELETE_CONFIRMATION_REQUIRED"
    assert preview.json()["affected_knowledge_count"] >= 1

    confirmed = client.delete("/api/data-tables/house_price_monthly?confirm=true")

    assert confirmed.status_code == 200
    assert confirmed.json()["linked_items_removed"] >= 1
    assert confirmed.json()["table_status"] == "unavailable"
