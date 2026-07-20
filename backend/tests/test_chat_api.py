from sqlalchemy import text


def test_default_domain_config_exposes_real_estate_tables():
    from app.domain import get_default_domain_config

    config = get_default_domain_config()

    assert "house_price_monthly" in config.allowed_tables
    assert "海淀区" in config.districts
    candidate_fields = {
        field
        for _, candidates in config.chart_field_priority
        for field in candidates
    }
    assert "avg_price" in candidate_fields
    assert config.tool_labels["knowledge_retriever"] == "知识库检索工具"


def test_conversation_package_keeps_public_imports():
    from app.services.conversation import (
        get_analysis,
        get_conversation_history,
        list_conversations,
        run_chat,
    )

    assert callable(run_chat)
    assert callable(get_analysis)
    assert callable(list_conversations)
    assert callable(get_conversation_history)


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
    assert "2.3" in second["requirement_ids"]


def test_follow_up_relative_previous_year_updates_context_and_query(client):
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
        json={
            "conversation_id": conversation_id,
            "question": "那上一年呢",
        },
    ).json()

    assert first["context"]["year_from"] == 2025
    assert second["context"]["year_from"] == 2024
    assert second["context"]["year_to"] == 2024
    assert "2024" in second["queries"][0]["sql"]
    assert "2025" not in second["queries"][0]["sql"]


def test_follow_up_district_alias_keeps_previous_year(client):
    conversation_id = client.post("/api/conversations").json()["id"]
    client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "question": "分析2025年各区平均房价",
        },
    )
    follow_up = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "question": "那朝阳呢"},
    ).json()

    assert follow_up["context"]["year_from"] == 2025
    assert follow_up["context"]["district"] == "朝阳区"
    assert {row["district"] for row in follow_up["datasets"][0]["rows"]} == {"朝阳区"}


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


def test_conversation_history_can_be_listed_and_restored(client):
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

    conversations = client.get("/api/conversations").json()
    current = conversations[0]

    assert current["id"] == conversation_id
    assert current["title"] == "分析2025年各区平均房价"
    assert current["latest_question"] == "只看海淀区"
    assert current["analysis_count"] == 2

    detail = client.get(f"/api/conversations/{conversation_id}").json()

    assert detail["id"] == conversation_id
    assert [item["question"] for item in detail["exchanges"]] == [
        "分析2025年各区平均房价",
        "只看海淀区",
    ]
    assert detail["exchanges"][0]["response"] == first
    assert detail["exchanges"][1]["response"] == second


def test_conversation_history_can_be_deleted(client):
    conversation_id = client.post("/api/conversations").json()["id"]
    analysis = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "question": "分析2025年各区平均房价",
        },
    ).json()

    response = client.delete(f"/api/conversations/{conversation_id}")

    assert response.status_code == 204
    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert client.get(f"/api/analysis/{analysis['analysis_id']}").status_code == 404
    assert all(item["id"] != conversation_id for item in client.get("/api/conversations").json())


def test_conversation_history_can_be_cleared(client):
    first = client.post("/api/conversations").json()["id"]
    second = client.post("/api/conversations").json()["id"]
    for conversation_id in [first, second]:
        client.post(
            "/api/chat",
            json={
                "conversation_id": conversation_id,
                "question": "分析2025年各区平均房价",
            },
        )

    response = client.delete("/api/conversations")

    assert response.status_code == 204
    assert client.get("/api/conversations").json() == []
    assert client.get(f"/api/conversations/{first}").status_code == 404
    assert client.get(f"/api/conversations/{second}").status_code == 404


def test_unknown_conversation_uses_public_error_shape(client):
    response = client.post(
        "/api/chat",
        json={"conversation_id": "missing", "question": "分析2025年房价"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "CONVERSATION_NOT_FOUND"
    assert response.json()["action"] == "请新建会话后重试"
    assert response.json()["request_id"]
