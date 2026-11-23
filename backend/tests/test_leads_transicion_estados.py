"""Tests TDD para 002-04: PATCH /admin/leads/{lead_id} (transiciones y asignación).

Fuente: docs/specs/specs_funcionalidad/002-cotizacion-b2b/002-04-transicion-estados-asignacion-agente.md
"""

from datetime import datetime, timedelta


def _create_lead(client, email: str = "ada@empresa.com") -> dict:
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


def _admin_id(db) -> int:
    from sqlalchemy import select

    with db.SessionLocal() as session:
        return session.scalar(select(db.User).where(db.User.is_admin.is_(True))).id


def _set_status(db, lead_id: int, lead_status: str) -> None:
    with db.SessionLocal() as session:
        lead = session.get(db.Lead, lead_id)
        lead.status = lead_status
        session.commit()


def test_patch_lead_changes_status_and_assigns_agent(client, db, auth_headers):
    # Arrange: lead recibido y agente admin existente
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)
    agent_id = _admin_id(db)

    # Act
    response = client.patch(
        f"/admin/leads/{lead['id']}",
        json={"status": "en_revision", "assigned_agent_id": agent_id},
        headers=headers,
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "en_revision"
    assert data["assigned_agent_id"] == agent_id


def test_patch_lead_rejects_invalid_transition(client, db, auth_headers):
    # Arrange: lead recibido
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)

    # Act: salto inválido recibido -> cotizado
    response = client.patch(
        f"/admin/leads/{lead['id']}", json={"status": "cotizado"}, headers=headers
    )

    # Assert: 400 con el formato acordado
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Transición inválida: recibido -> cotizado. "
        "Permitidas desde recibido: en_revision, cerrado"
    )


def test_patch_lead_404_when_agent_not_found(client, db, auth_headers):
    # Arrange: lead existente
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)

    # Act
    response = client.patch(
        f"/admin/leads/{lead['id']}", json={"assigned_agent_id": 99999}, headers=headers
    )

    # Assert
    assert response.status_code == 404


def test_patch_lead_404_when_agent_not_admin(client, db, auth_headers):
    """El agente debe existir y ser admin (hoy no hay rol agent)."""
    # Arrange: usuario normal (no admin) como objetivo de asignación
    admin_headers = auth_headers(email="admin@test.com", is_admin=True)
    auth_headers(email="user@test.com")  # crea el usuario no-admin
    lead = _create_lead(client)
    from sqlalchemy import select

    with db.SessionLocal() as session:
        user_id = session.scalar(
            select(db.User).where(db.User.email == "user@test.com")
        ).id

    # Act
    response = client.patch(
        f"/admin/leads/{lead['id']}",
        json={"assigned_agent_id": user_id},
        headers=admin_headers,
    )

    # Assert: 404 (no existe *como agente válido*)
    assert response.status_code == 404


def test_patch_lead_closes_from_any_state(client, db, auth_headers):
    # Arrange: un lead en cada estado previo
    headers = auth_headers(email="admin@test.com", is_admin=True)
    ids = []
    for i, prev_status in enumerate(("recibido", "en_revision", "cotizado")):
        lead = _create_lead(client, email=f"lead{i}@test.com")
        _set_status(db, lead["id"], prev_status)
        ids.append(lead["id"])

    # Act/Assert: cerrado alcanzable desde cualquier estado
    for lead_id in ids:
        response = client.patch(
            f"/admin/leads/{lead_id}", json={"status": "cerrado"}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cerrado"


def test_patch_lead_rejects_transitions_from_cerrado(client, db, auth_headers):
    """Caso borde (§5.5 del padre): cerrado es terminal, toda transición es 400."""
    # Arrange: lead cerrado
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)
    _set_status(db, lead["id"], "cerrado")

    # Act
    response = client.patch(
        f"/admin/leads/{lead['id']}", json={"status": "en_revision"}, headers=headers
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Transición inválida: cerrado -> en_revision. Permitidas desde cerrado: ninguna"
    )


def test_patch_lead_rejects_cotizado_to_en_revision(client, db, auth_headers):
    # Arrange: lead cotizado
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)
    _set_status(db, lead["id"], "cotizado")

    # Act: transición de retroceso inválida
    response = client.patch(
        f"/admin/leads/{lead['id']}", json={"status": "en_revision"}, headers=headers
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Transición inválida: cotizado -> en_revision. "
        "Permitidas desde cotizado: cerrado"
    )


def test_patch_lead_rejects_empty_body(client, db, auth_headers):
    # Arrange: lead existente
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)

    # Act: body sin status ni assigned_agent_id
    response = client.patch(f"/admin/leads/{lead['id']}", json={}, headers=headers)

    # Assert
    assert response.status_code == 422


def test_patch_lead_rejects_unknown_status_value(client, db, auth_headers):
    """Un status fuera del enum es 422 (validación de esquema)."""
    # Arrange
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)

    # Act
    response = client.patch(
        f"/admin/leads/{lead['id']}", json={"status": "congelado"}, headers=headers
    )

    # Assert
    assert response.status_code == 422


def test_patch_lead_404_when_lead_not_found(client, db, auth_headers):
    # Arrange: token admin, lead inexistente
    headers = auth_headers(email="admin@test.com", is_admin=True)

    # Act
    response = client.patch(
        "/admin/leads/9999", json={"status": "en_revision"}, headers=headers
    )

    # Assert
    assert response.status_code == 404


def test_patch_lead_requires_auth(client, db):
    # Arrange: lead existente, sin token
    lead = _create_lead(client)

    # Act
    response = client.patch(f"/admin/leads/{lead['id']}", json={"status": "en_revision"})

    # Assert: 401 (HTTPBearer de FastAPI >= 0.122)
    assert response.status_code == 401


def test_patch_lead_requires_admin(client, db, auth_headers):
    # Arrange: lead existente, token de usuario normal
    lead = _create_lead(client)
    headers = auth_headers(email="user@test.com")

    # Act
    response = client.patch(
        f"/admin/leads/{lead['id']}", json={"status": "en_revision"}, headers=headers
    )

    # Assert
    assert response.status_code == 403


def test_patch_lead_assigns_agent_without_status_change(client, db, auth_headers):
    # Arrange: lead recibido y agente admin
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)
    agent_id = _admin_id(db)

    # Act: solo asignación
    response = client.patch(
        f"/admin/leads/{lead['id']}",
        json={"assigned_agent_id": agent_id},
        headers=headers,
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_agent_id"] == agent_id
    assert data["status"] == "recibido"  # sin cambios


def test_patch_lead_updates_updated_at(client, db, auth_headers):
    # Arrange
    headers = auth_headers(email="admin@test.com", is_admin=True)
    lead = _create_lead(client)
    previous = datetime.fromisoformat(lead["created_at"])

    # Act
    response = client.patch(
        f"/admin/leads/{lead['id']}", json={"status": "en_revision"}, headers=headers
    )

    # Assert
    assert response.status_code == 200
    updated_at = datetime.fromisoformat(response.json()["updated_at"])
    assert updated_at >= previous
    assert updated_at > previous - timedelta(seconds=1)
