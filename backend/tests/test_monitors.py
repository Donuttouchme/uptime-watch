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


def create_three(client):
    return [
        create(client, url=f"https://example{n}.com", name=f"Example {n}").json()
        for n in (1, 2, 3)
    ]


def test_list_empty(client):
    response = client.get(MONITORS)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_list_pages_in_id_order(client):
    created = create_three(client)

    first = client.get(MONITORS, params={"limit": 2}).json()
    rest = client.get(MONITORS, params={"limit": 2, "offset": 2}).json()

    assert [m["id"] for m in first["items"]] == [created[0]["id"], created[1]["id"]]
    assert first["total"] == 3
    assert [m["id"] for m in rest["items"]] == [created[2]["id"]]


def test_list_offset_past_end_returns_empty_page(client):
    create_three(client)

    body = client.get(MONITORS, params={"offset": 10}).json()

    assert body["items"] == []
    assert body["total"] == 3


def test_list_rejects_limit_out_of_range(client):
    assert client.get(MONITORS, params={"limit": 0}).status_code == 422
    assert client.get(MONITORS, params={"limit": 201}).status_code == 422


def test_patch_changes_only_given_fields(client):
    created = create(client).json()

    response = client.patch(f"{MONITORS}/{created['id']}", json={"name": "Renamed", "paused": True})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["paused"] is True
    assert body["url"] == created["url"]
    assert body["interval_seconds"] == created["interval_seconds"]


def test_patch_rejects_explicit_null(client):
    created = create(client).json()

    response = client.patch(f"{MONITORS}/{created['id']}", json={"name": None})

    assert response.status_code == 422


def test_patch_rejects_interval_below_30_seconds(client):
    created = create(client).json()

    response = client.patch(f"{MONITORS}/{created['id']}", json={"interval_seconds": 10})

    assert response.status_code == 422


def test_patch_url_to_existing_url_returns_409(client):
    first, second, _ = create_three(client)

    response = client.patch(f"{MONITORS}/{second['id']}", json={"url": first["url"]})

    assert response.status_code == 409


def test_patch_unknown_monitor_returns_404(client):
    assert client.patch(f"{MONITORS}/999", json={"name": "x"}).status_code == 404


def test_delete_removes_monitor(client):
    created = create(client).json()

    response = client.delete(f"{MONITORS}/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"{MONITORS}/{created['id']}").status_code == 404


def test_delete_unknown_monitor_returns_404(client):
    assert client.delete(f"{MONITORS}/999").status_code == 404
