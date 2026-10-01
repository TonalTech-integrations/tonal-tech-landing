from datetime import timedelta


def test_checkout_session_requires_auth(client, db):
    response = client.post("/payments/checkout-session", json={"course_id": "plc-industrial"})

    assert response.status_code in (401, 403)


def test_checkout_session_rejects_invalid_token(client, db):
    response = client.post(
        "/payments/checkout-session",
        json={"course_id": "plc-industrial"},
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert response.status_code == 401


def test_checkout_session_rejects_expired_token(client, db, auth_headers):
    from backend.routers.auth import create_access_token

    auth_headers()
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-10))

    response = client.post(
        "/payments/checkout-session",
        json={"course_id": "plc-industrial"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_checkout_session_allowed_with_valid_token(client, db, auth_headers):
    response = client.post(
        "/payments/checkout-session",
        json={"course_id": "plc-industrial"},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["session_id"]


def test_checkout_session_uses_token_email_not_payload(client, db, auth_headers):
    headers = auth_headers(email="owner@test.com")

    response = client.post(
        "/payments/checkout-session",
        json={"course_id": "plc-industrial", "customer_email": "otro@test.com"},
        headers=headers,
    )

    purchase = db.get_purchase_by_session(response.json()["session_id"])
    assert purchase.customer_email == "owner@test.com"
