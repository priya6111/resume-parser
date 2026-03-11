import routes.parse as parse_routes


def test_candidates_history_returns_items_and_respects_limit_cap(client, monkeypatch):
    captured = {}

    def fake_get_recent_candidates(limit=20):
        captured["limit"] = limit
        return [
            {
                "id": "1",
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "+911234567890",
                "skills": ["Python"],
                "created_at": "2026-03-11T10:00:00+00:00",
            }
        ]

    monkeypatch.setattr(parse_routes, "get_recent_candidates", fake_get_recent_candidates)

    response = client.get("/candidates?limit=1000")

    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 1
    assert body["items"][0]["name"] == "Jane Doe"
    assert captured["limit"] == 100


def test_candidates_history_returns_warning_on_failure(client, monkeypatch):
    def fake_get_recent_candidates(limit=20):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(parse_routes, "get_recent_candidates", fake_get_recent_candidates)

    response = client.get("/candidates")

    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 0
    assert body["items"] == []
    assert "Database is currently unavailable" in body["warning"]
