from pathlib import Path
from types import SimpleNamespace

from backend.services.persistence import Course, SessionLocal

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _backend_source_files():
    for path in sorted(BACKEND_DIR.rglob("*.py")):
        if "tests" in path.parts or "__pycache__" in path.parts:
            continue
        yield path


def test_price_map_removed():
    for path in _backend_source_files():
        content = path.read_text()
        assert "PRICE_MAP" not in content, path
        assert "COURSE_VIDEO_KEYS" not in content, path
        assert "CourseId" not in content, path


def test_checkout_uses_course_specific_price(monkeypatch, client, db, auth_headers):
    import stripe

    from backend.services import stripe as stripe_service

    db.create_course("mi-curso-nuevo", "Mi Curso Nuevo", price_cents=9900)
    with SessionLocal() as session:
        course = session.get(Course, "mi-curso-nuevo")
        course.stripe_price_id = "price_curso_nuevo"
        session.commit()

    monkeypatch.setattr(stripe_service.settings, "payments_mock", False)
    captured = {}

    def fake_create(**kwargs):
        captured["line_items"] = kwargs["line_items"]
        return SimpleNamespace(id="cs_test_1", url="http://checkout.test")

    monkeypatch.setattr(stripe.checkout.Session, "create", fake_create)

    response = client.post(
        "/payments/checkout-session",
        json={"course_id": "mi-curso-nuevo"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    assert captured["line_items"][0]["price"] == "price_curso_nuevo"


def test_checkout_accepts_course_not_in_old_enum(client, db, auth_headers):
    db.create_course("mi-curso-nuevo", "Mi Curso Nuevo", price_cents=9900)
    response = client.post(
        "/payments/checkout-session",
        json={"course_id": "mi-curso-nuevo"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["session_id"].startswith("cs_mock_")


def test_checkout_404_for_unknown_course_id_string(client, db, auth_headers):
    response = client.post(
        "/payments/checkout-session",
        json={"course_id": "curso-inexistente"},
        headers=auth_headers(),
    )
    assert response.status_code == 404


def test_purchase_course_id_is_plain_string(db):
    db.create_purchase_record("cs_str_1", "mi-curso-nuevo", "buyer@test.com", "videos/mi-curso-nuevo")
    purchase = db.get_purchase_by_session("cs_str_1")
    assert isinstance(purchase.course_id, str)
    assert purchase.course_id == "mi-curso-nuevo"


def test_seed_courses_still_purchasable_in_mock(client, db, auth_headers):
    email = "seed-buyer@test.com"
    headers = auth_headers(email=email)
    user = db.get_user_by_email(email)
    for course_id in ("plc-industrial", "scada-redes", "robotica-industrial"):
        response = client.post(
            "/payments/checkout-session",
            json={"course_id": course_id},
            headers=headers,
        )
        assert response.status_code == 200
        assert db.has_enrollment(user.id, course_id)
