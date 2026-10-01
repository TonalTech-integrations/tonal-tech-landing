from datetime import timedelta

BODY = {"object_key": "videos/test/leccion-1.mp4"}


def test_upload_url_requires_auth(client, db):
    response = client.post("/videos/upload-url", json=BODY)

    assert response.status_code in (401, 403)


def test_upload_url_forbidden_for_non_admin(client, db, auth_headers):
    headers = auth_headers()

    response = client.post("/videos/upload-url", json=BODY, headers=headers)

    assert response.status_code == 403


def test_upload_url_allowed_for_admin(client, db, auth_headers):
    headers = auth_headers(email="admin@test.com", is_admin=True)

    response = client.post("/videos/upload-url", json=BODY, headers=headers)

    assert response.status_code == 200
    assert response.json()["upload_url"]
    assert response.json()["object_key"] == BODY["object_key"]


def test_upload_url_invalid_token_returns_401(client, db):
    headers = {"Authorization": "Bearer token-invalido"}

    response = client.post("/videos/upload-url", json=BODY, headers=headers)

    assert response.status_code == 401


def test_upload_url_expired_token_returns_401(client, db, auth_headers):
    from backend.routers.auth import create_access_token

    auth_headers(email="admin@test.com", is_admin=True)
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-10))

    response = client.post("/videos/upload-url", json=BODY, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_upload_url_empty_object_key_returns_422(client, db, auth_headers):
    headers = auth_headers(email="admin@test.com", is_admin=True)

    response = client.post("/videos/upload-url", json={"object_key": ""}, headers=headers)

    assert response.status_code == 422
