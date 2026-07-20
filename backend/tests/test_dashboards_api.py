def test_dashboard_round_trip_preserves_card_layout(client):
    dashboard = client.post("/api/dashboards", json={"name": "房价分析看板"}).json()
    card = client.post(
        f"/api/dashboards/{dashboard['id']}/cards",
        json={
            "title": "各区平均房价",
            "analysis_id": "demo-analysis",
            "chart": {"type": "bar", "x_field": "district", "y_fields": ["avg_price"], "title": "各区平均房价"},
            "layout": {"x": 0, "y": 0, "w": 6, "h": 4},
        },
    ).json()

    patched = client.patch(
        f"/api/dashboards/{dashboard['id']}/layout",
        json={"cards": [{"id": card["id"], "x": 6, "y": 0, "w": 6, "h": 5}]},
    )
    saved = client.get(f"/api/dashboards/{dashboard['id']}").json()

    assert patched.status_code == 200
    assert saved["cards"][0]["layout"] == {"x": 6, "y": 0, "w": 6, "h": 5}
    assert saved["share_id"]


def test_dashboard_share_view_and_card_removal(client):
    dashboard = client.post("/api/dashboards", json={"name": "共享看板"}).json()
    card = client.post(
        f"/api/dashboards/{dashboard['id']}/cards",
        json={
            "title": "趋势图",
            "analysis_id": "demo-analysis",
            "chart": {"type": "line", "x_field": "month", "y_fields": ["avg_price"], "title": "趋势图"},
            "layout": {"x": 0, "y": 0, "w": 12, "h": 4},
        },
    ).json()

    shared = client.get(f"/api/dashboards/share/{dashboard['share_id']}")
    removed = client.delete(f"/api/dashboards/{dashboard['id']}/cards/{card['id']}")

    assert shared.status_code == 200
    assert shared.json()["name"] == "共享看板"
    assert removed.status_code == 204
    assert client.get(f"/api/dashboards/{dashboard['id']}").json()["cards"] == []


def test_dashboard_can_be_renamed(client):
    dashboard = client.post("/api/dashboards", json={"name": "旧名称"}).json()

    response = client.patch(
        f"/api/dashboards/{dashboard['id']}",
        json={"name": "2025区域成交看板"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "2025区域成交看板"
    assert client.get(f"/api/dashboards/{dashboard['id']}").json()["name"] == "2025区域成交看板"
    assert client.get(f"/api/dashboards/share/{dashboard['share_id']}").json()["name"] == "2025区域成交看板"


def test_dashboard_and_share_reuse_the_saved_analysis_datasets(client):
    conversation = client.post("/api/conversations").json()
    analysis = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation["id"],
            "question": "分析2025年各区平均房价",
        },
    ).json()
    dashboard = client.post("/api/dashboards", json={"name": "同源数据看板"}).json()

    client.post(
        f"/api/dashboards/{dashboard['id']}/cards",
        json={
            "title": analysis["chart"]["title"],
            "analysis_id": analysis["analysis_id"],
            "chart": analysis["chart"],
            "layout": {"x": 0, "y": 0, "w": 6, "h": 4},
        },
    )

    saved_card = client.get(f"/api/dashboards/{dashboard['id']}").json()["cards"][0]
    shared_card = client.get(f"/api/dashboards/share/{dashboard['share_id']}").json()["cards"][0]

    assert saved_card["datasets"] == analysis["datasets"]
    assert shared_card["datasets"] == analysis["datasets"]


def test_dashboard_layout_rejects_negative_coordinates(client):
    dashboard = client.post("/api/dashboards", json={"name": "布局校验"}).json()

    response = client.post(
        f"/api/dashboards/{dashboard['id']}/cards",
        json={
            "title": "非法卡片",
            "analysis_id": "demo-analysis",
            "chart": {"type": "bar", "x_field": "district", "y_fields": ["avg_price"], "title": "非法卡片"},
            "layout": {"x": -1, "y": 0, "w": 6, "h": 4},
        },
    )

    assert response.status_code == 422
