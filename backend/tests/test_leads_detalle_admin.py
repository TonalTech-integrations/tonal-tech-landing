"""Tests TDD para 002-03: GET /admin/leads/{lead_id} (detalle de lead, admin).

Fuente: docs/specs/specs_funcionalidad/002-cotizacion-b2b/002-03-detalle-lead-admin.md
"""

from datetime import date

from sqlalchemy import delete, select

from backend.services.persistence import Quote, QuoteParams


def _create_lead(client, email: str) -> dict:
    response = client.post(
        "/leads",
        json={
            "service_category": "ciberseguridad",
            "contact_name": "Ada Lovelace",
            "email": email,
            "company_size": "Mediana empresa",
            "message": "Mensaje de prueba con longitud suficiente.",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_quote(db, lead_id: int, created_by: int) -> Quote:
    """Crea la cotización directamente en BD (la creación vía API es 002-05)."""
    with db.SessionLocal() as session:
        admin = session.scalar(select(db.User).where(db.User.is_admin.is_(True)))
        quote = Quote(
            lead_id=lead_id,
            amount_cents=150000,
            currency="mxn",
            valid_until=date(2026, 12, 31),
            notes="Incluye soporte 3 meses",
            created_by=admin.id if created_by is None else created_by,
        )
        session.add(quote)
        session.commit()
        session.refresh(quote)
        return quote


def _delete_quote_params(db, lead_id: int) -> None:
    with db.SessionLocal() as session:
        session.execute(delete(QuoteParams).where(QuoteParams.lead_id == lead_id))
        session.commit()


def test_get_lead_detail_returns_lead_quote_and_params(client, db, auth_headers):
    # Arrange: lead con cotización (creada en BD; la API de creación es 002-05)
    # y quote_params v1 (creado automáticamente por POST /leads)
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client, "ada@empresa.com")
    quote = _create_quote(db, lead["id"], created_by=0)

    # Act
    response = client.get(f"/admin/leads/{lead['id']}", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["lead"]["id"] == lead["id"]
    assert data["lead"]["message"] == "Mensaje de prueba con longitud suficiente."
    assert data["lead"]["status"] == "recibido"
    assert data["quote"] is not None
    assert data["quote"]["id"] == quote.id
    assert data["quote"]["amount_cents"] == 150000
    assert data["quote"]["currency"] == "mxn"
    assert data["quote"]["valid_until"] == "2026-12-31"
    assert data["quote"]["notes"] == "Incluye soporte 3 meses"
    assert data["quote_params"] is not None
    assert data["quote_params"]["service_category"] == "ciberseguridad"
    assert data["quote_params"]["version"] == 1
    assert data["quote_params"]["params"]["message"] == (
        "Mensaje de prueba con longitud suficiente."
    )


def test_get_lead_detail_404_when_not_found(client, db, auth_headers):
    # Arrange: token admin y lead_id inexistente
    headers = auth_headers(email="admin@test.com", is_admin=True)

    # Act
    response = client.get("/admin/leads/9999", headers=headers)

    # Assert
    assert response.status_code == 404


def test_get_lead_detail_quote_null_when_no_quote(client, db, auth_headers):
    # Arrange: lead sin cotización (con quote_params v1 de 002-01)
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client, "ada@empresa.com")

    # Act
    response = client.get(f"/admin/leads/{lead['id']}", headers=headers)

    # Assert: quote null, quote_params presente (corrección 2026-10-01, decisión §5.3)
    assert response.status_code == 200
    data = response.json()
    assert data["quote"] is None
    assert data["quote_params"] is not None
    assert data["quote_params"]["version"] == 1


def test_get_lead_detail_without_quote_params_returns_nulls(client, db, auth_headers):
    """Caso legado: lead sin fila quote_params -> ambos null (no 404)."""
    # Arrange
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client, "ada@empresa.com")
    _delete_quote_params(db, lead["id"])

    # Act
    response = client.get(f"/admin/leads/{lead['id']}", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["quote"] is None
    assert data["quote_params"] is None


def test_get_lead_detail_requires_auth(client, db):
    # Arrange: lead creado vía API pública; sin token
    lead = _create_lead(client, "ada@empresa.com")

    # Act
    response = client.get(f"/admin/leads/{lead['id']}")

    # Assert: 401 (HTTPBearer de FastAPI >= 0.122)
    assert response.status_code == 401


def test_get_lead_detail_requires_admin(client, db, auth_headers):
    # Arrange: lead y token de usuario normal
    lead = _create_lead(client, "ada@empresa.com")
    headers = auth_headers(email="user@test.com")

    # Act
    response = client.get(f"/admin/leads/{lead['id']}", headers=headers)

    # Assert
    assert response.status_code == 403
