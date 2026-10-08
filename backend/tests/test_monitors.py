MONITORS = "/api/v1/monitors"


def create(client, url="https://example.com", **fields):
    body = {"name": "Example", "url": url, **fields}
    return client.post(MONITORS, json=body)


def test_create_monitor_returns_201_with_defaults(client):
    response = create(client)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] >= 1
    assert body["name"] == "Example"
    assert body["url"] == "https://example.com/"
    assert body["interval_seconds"] == 60
    assert body["paused"] is False
    assert "created_at" in body


def test_create_duplicate_url_returns_409(client):
    create(client)

    response = create(client, name="Again")

    assert response.status_code == 409
    assert response.json() == {"detail": "A monitor for this URL already exists"}


def test_create_duplicate_url_with_different_spelling_returns_409(client):
    create(client, url="https://Example.com")

    response = create(client, url="https://example.com/")

    assert response.status_code == 409


def test_create_rejects_non_http_url(client):
    assert create(client, url="ftp://example.com").status_code == 422


def test_create_rejects_interval_below_30_seconds(client):
    assert create(client, interval_seconds=29).status_code == 422
    assert create(client, url="https://example.org", interval_seconds=30).status_code == 201


def test_create_rejects_empty_name(client):
    assert create(client, name="").status_code == 422


def test_get_monitor_returns_it(client):
    created = create(client).json()

    response = client.get(f"{MONITORS}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_monitor_returns_404(client):
    response = client.get(f"{MONITORS}/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}
