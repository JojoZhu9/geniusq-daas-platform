from sqlalchemy import text


def test_incomplete_question_returns_recommendations_without_querying(client):
    conversation = client.post("/api/conversations").json()

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation["id"], "question": "分析房价"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert len(body["suggestions"]) == 3
    assert body["queries"] == []
    assert body["datasets"] == []


def test_follow_up_inherits_year_and_overrides_district(client):
    conversation_id = client.post("/api/conversations").json()["id"]
    first = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "question": "分析2025年各区平均房价",
        },
    ).json()
    second = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "只看海淀区"},
    ).json()

    assert first["status"] == "completed"
    assert first["context"]["year_from"] == 2025
    assert second["context"] == {
        "year_from": 2025,
        "year_to": 2025,
        "district": "海淀区",
        "metric": "平均房价",
    }
    assert {row["district"] for row in second["datasets"][0]["rows"]} == {"海淀区"}


def test_completed_analysis_can_be_reloaded(client):
    conversation_id = client.post("/api/conversations").json()["id"]
    created = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "question": "2025年房价上涨是否与人口和通勤相关",
        },
    ).json()

    loaded = client.get(f"/api/analysis/{created['analysis_id']}")

    assert loaded.status_code == 200
    assert loaded.json() == created
    assert len(loaded.json()["queries"]) == 2
    assert len(loaded.json()["datasets"]) == 2


def test_unknown_conversation_uses_public_error_shape(client):
    response = client.post(
        "/api/chat",
        json={"conversation_id": "missing", "question": "分析2025年房价"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CONVERSATION_NOT_FOUND"
    assert response.json()["detail"]["action"] == "请新建会话后重试"
    assert response.json()["detail"]["request_id"]
