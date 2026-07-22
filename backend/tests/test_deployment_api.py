def test_root_health_endpoint_keeps_render_overview_green(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_vercel_origin_is_allowed_by_cors(client):
    response = client.options(
        "/api/conversations",
        headers={
            "Origin": "https://geniusq-daas-platform.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://geniusq-daas-platform.vercel.app"
