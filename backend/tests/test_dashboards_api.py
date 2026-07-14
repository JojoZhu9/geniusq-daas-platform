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
