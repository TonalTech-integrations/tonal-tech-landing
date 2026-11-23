def _url(course_id="plc-industrial", extra=""):
    return f"/videos/download-url?course_id={course_id}{extra}"


def test_download_url_requires_auth(client, db):
    response = client.get(_url())

    assert response.status_code in (401, 403)


def test_download_url_invalid_token_returns_401(client, db):
    response = client.get(_url(), headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 401


def test_download_url_forbidden_without_enrollment(client, db, auth_headers):
    response = client.get(_url(), headers=auth_headers())

    assert response.status_code == 403


def test_download_url_allowed_with_enrollment(client, db, auth_headers):
    headers = auth_headers()
    user = db.get_user_by_email("user@test.com")
    db.grant_enrollment(user.id, "plc-industrial")

    response = client.get(_url(), headers=headers)

    assert response.status_code == 200
    assert response.json()["download_url"]
    assert response.headers["Deprecation"] == "true"


def test_download_url_404_for_unknown_course(client, db, auth_headers):
    response = client.get(_url("curso-inexistente"), headers=auth_headers())

    assert response.status_code == 404


def test_download_url_ignores_customer_email_param(client, db, auth_headers):
    buyer_headers = auth_headers(email="buyer@test.com")
    buyer = db.get_user_by_email("buyer@test.com")
    db.grant_enrollment(buyer.id, "plc-industrial")
    other_headers = auth_headers(email="other@test.com")

    response = client.get(_url(extra="&customer_email=buyer@test.com"), headers=other_headers)

    assert response.status_code == 403
    assert client.get(_url(), headers=buyer_headers).status_code == 200
