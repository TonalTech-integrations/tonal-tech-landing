"""Tests TDD para 002-01: POST /leads (crear lead público).

Fuente: docs/specs/specs_funcionalidad/002-cotizacion-b2b/002-01-crear-lead-publico.md
"""

from sqlalchemy import select

VALID_PAYLOAD = {
    "service_category": "ciberseguridad",
    "contact_name": "Ada Lovelace",
    "email": "ada@empresa.com",
    "company_size": "Mediana empresa",
    "message": "Necesitamos una auditoría de seguridad completa.",
}


def test_create_lead_persists_with_status_recibido(client, db):
    # Arrange: payload válido con email correcto
    # Act
    response = client.post("/leads", json=VALID_PAYLOAD)

    # Assert: 201, estado inicial recibido, sin exponer message ni assigned_agent_id
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "recibido"
    assert data["service_category"] == "ciberseguridad"
    assert data["contact_name"] == "Ada Lovelace"
    assert data["email"] == "ada@empresa.com"
    assert data["company_size"] == "Mediana empresa"
    assert "created_at" in data
    assert "message" not in data
    assert "assigned_agent_id" not in data

    # Assert: el registro existe en BD
    lead = db.get_lead(data["id"])
    assert lead is not None
    assert lead.status == "recibido"
    assert lead.assigned_agent_id is None
    assert lead.message == VALID_PAYLOAD["message"]


def test_create_lead_rejects_invalid_email(client):
    # Arrange: email inválido
    # Act
    response = client.post("/leads", json={**VALID_PAYLOAD, "email": "no-es-email"})

    # Assert: 422 (validación Pydantic EmailStr)
    assert response.status_code == 422


def test_create_lead_rejects_unknown_service_category(client):
    # Arrange: categoría fuera de las 6 permitidas
    # Act
    response = client.post("/leads", json={**VALID_PAYLOAD, "service_category": "otra-cosa"})

    # Assert: 400
    assert response.status_code == 400


def test_create_lead_accepts_labs_and_academy_categories(client, db):
    # Arrange/Act: lead de consulta general para labs y academy
    for category in ("labs", "academy"):
        response = client.post("/leads", json={**VALID_PAYLOAD, "service_category": category})

        # Assert: 201, lead persistido con estado recibido
        assert response.status_code == 201
        lead = db.get_lead(response.json()["id"])
        assert lead is not None
        assert lead.service_category == category
        assert lead.status == "recibido"


def test_create_lead_rejects_unknown_company_size(client):
    # Arrange: company_size fuera de companySizes
    # Act
    response = client.post("/leads", json={**VALID_PAYLOAD, "company_size": "Micro empresa"})

    # Assert
    assert response.status_code == 422


def test_create_lead_rejects_message_too_short(client):
    # Arrange: message de 4 caracteres tras trim (mínimo 5)
    # Act
    response = client.post("/leads", json={**VALID_PAYLOAD, "message": "hola"})

    # Assert
    assert response.status_code == 422


def test_create_lead_normalizes_email_to_lowercase(client, db):
    # Arrange: email con mayúsculas
    # Act
    response = client.post("/leads", json={**VALID_PAYLOAD, "email": "Cliente@Empresa.com"})

    # Assert: el email persistido y devuelto es minúsculas
    assert response.status_code == 201
    assert response.json()["email"] == "cliente@empresa.com"
    lead = db.get_lead(response.json()["id"])
    assert lead.email == "cliente@empresa.com"


def test_create_lead_rejects_contact_name_too_short(client):
    # Arrange: contact_name de 1 carácter (mínimo 2)
    # Act
    response = client.post("/leads", json={**VALID_PAYLOAD, "contact_name": "A"})

    # Assert
    assert response.status_code == 422


def test_create_lead_rejects_message_with_only_spaces(client):
    # Arrange: message solo espacios (tras trim, longitud 0 < 5)
    # Act
    response = client.post("/leads", json={**VALID_PAYLOAD, "message": "     "})

    # Assert
    assert response.status_code == 422


def test_create_lead_rejects_missing_required_fields(client):
    # Arrange: body vacío
    # Act
    response = client.post("/leads", json={})

    # Assert: 422 por campos requeridos ausentes
    assert response.status_code == 422


def test_create_lead_public_without_token(client):
    # Arrange/Act: sin header Authorization
    response = client.post("/leads", json=VALID_PAYLOAD)

    # Assert: endpoint público, 201
    assert response.status_code == 201


def test_create_lead_creates_quote_params_versioned(client, db):
    """Decisión aprobada 2026-10-01 (spec 002 §5.3): quote_params se crea con el lead."""
    # Arrange/Act
    response = client.post("/leads", json=VALID_PAYLOAD)

    # Assert: existe quote_params version=1 con el mensaje estructurado
    assert response.status_code == 201
    lead_id = response.json()["id"]
    with db.SessionLocal() as session:
        params = session.scalar(select(db.QuoteParams).where(db.QuoteParams.lead_id == lead_id))
    assert params is not None
    assert params.version == 1
    assert params.service_category == "ciberseguridad"
    assert params.params["message"] == VALID_PAYLOAD["message"]
