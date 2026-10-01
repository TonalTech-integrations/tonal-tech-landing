"""Tests TDD para 002-02: GET /admin/leads (listar leads, admin).

Fuente: docs/specs/specs_funcionalidad/002-cotizacion-b2b/002-02-listar-leads-admin.md
"""

from datetime import datetime


def _create_lead(db, email: str, service_category: str = "ciberseguridad") -> int:
    lead = db.create_lead(
        service_category=service_category,
        contact_name="Ada Lovelace",
        email=email,
        company_size="Mediana empresa",
        message="Mensaje de prueba con longitud suficiente.",
    )
    return lead.id


def _set_created_at(db, lead_id: int, when: datetime) -> None:
    with db.SessionLocal() as session:
        lead = session.get(db.Lead, lead_id)
        lead.created_at = when
        session.commit()


def _set_status(db, lead_id: int, lead_status: str) -> None:
    with db.SessionLocal() as session:
        lead = session.get(db.Lead, lead_id)
        lead.status = lead_status
        session.commit()


def test_list_leads_requires_admin(client, db, auth_headers):
    # Arrange: usuario autenticado sin rol admin
    headers = auth_headers(email="user@test.com")

    # Act
    response = client.get("/admin/leads", headers=headers)

    # Assert
    assert response.status_code == 403


def test_list_leads_requires_auth(client):
    # Arrange/Act: sin token
    response = client.get("/admin/leads")

    # Assert: 401 (HTTPBearer de FastAPI >= 0.122)
    assert response.status_code == 401


def test_list_leads_filters_by_status_and_category(client, db, auth_headers):
    # Arrange: 3 leads (2 recibido, 1 cotizado; 2 de ciberseguridad)
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead_a = _create_lead(db, "a@test.com", service_category="ciberseguridad")
    _create_lead(db, "b@test.com", service_category="labs")
    lead_c = _create_lead(db, "c@test.com", service_category="ciberseguridad")
    _set_status(db, lead_c, "cotizado")

    # Act
    response = client.get(
        "/admin/leads?status=recibido&service_category=ciberseguridad", headers=headers
    )

    # Assert: solo el lead que cumple ambos filtros
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [item["id"] for item in data["items"]] == [lead_a]
    item = data["items"][0]
    assert item["status"] == "recibido"
    assert item["assigned_agent_id"] is None
    assert "updated_at" in item
    assert "message" not in item  # el mensaje solo va en el detalle (002-03)


def test_list_leads_orders_by_created_at_desc(client, db, auth_headers):
    # Arrange: 2 leads con fechas distintas
    headers = auth_headers(email="admin@test.com", is_admin=True)
    old_id = _create_lead(db, "viejo@test.com")
    new_id = _create_lead(db, "nuevo@test.com")
    _set_created_at(db, old_id, datetime(2026, 9, 1, 10, 0, 0))
    _set_created_at(db, new_id, datetime(2026, 10, 1, 10, 0, 0))

    # Act
    response = client.get("/admin/leads", headers=headers)

    # Assert: el más reciente primero
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids[:2] == [new_id, old_id]


def test_list_leads_filters_by_date_range(client, db, auth_headers):
    # Arrange: un lead dentro del rango y otro fuera
    headers = auth_headers(email="admin@test.com", is_admin=True)
    inside_id = _create_lead(db, "dentro@test.com")
    outside_id = _create_lead(db, "fuera@test.com")
    _set_created_at(db, inside_id, datetime(2026, 9, 20, 12, 0, 0))
    _set_created_at(db, outside_id, datetime(2026, 8, 15, 12, 0, 0))

    # Act
    response = client.get("/admin/leads?from=2026-09-01&to=2026-09-30", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == inside_id


def test_list_leads_paginates_with_total(client, db, auth_headers):
    # Arrange: 25 leads
    headers = auth_headers(email="admin@test.com", is_admin=True)
    for i in range(25):
        _create_lead(db, f"lead{i}@test.com")

    # Act
    response = client.get("/admin/leads?page=2&page_size=10", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 2
    assert data["page_size"] == 10


def test_list_leads_rejects_page_size_over_100(client, db, auth_headers):
    # Arrange: token admin
    headers = auth_headers(email="admin@test.com", is_admin=True)

    # Act
    response = client.get("/admin/leads?page_size=101", headers=headers)

    # Assert: 422 (máx. 100, decisión confirmada 8.2 del padre)
    assert response.status_code == 422


def test_list_leads_empty_result_with_total_zero(client, db, auth_headers):
    # Arrange: sin leads
    headers = auth_headers(email="admin@test.com", is_admin=True)

    # Act
    response = client.get("/admin/leads", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_leads_rejects_invalid_date(client, db, auth_headers):
    # Arrange: token admin
    headers = auth_headers(email="admin@test.com", is_admin=True)

    # Act
    response = client.get("/admin/leads?from=no-es-fecha", headers=headers)

    # Assert
    assert response.status_code == 422


def test_list_leads_page_out_of_range_returns_empty(client, db, auth_headers):
    """Caso borde (§4): page fuera de rango -> lista vacía, no error."""
    # Arrange: 3 leads, se pide la página 5 con tamaño 20
    headers = auth_headers(email="admin@test.com", is_admin=True)
    for i in range(3):
        _create_lead(db, f"lead{i}@test.com")

    # Act
    response = client.get("/admin/leads?page=5&page_size=20", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 3
