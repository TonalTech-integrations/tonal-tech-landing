# 002-04 - Transición de estados y asignación de agente (PATCH /admin/leads/{id})

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.2, 5.5, 8.3, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 002-01 (el lead a actualizar se crea vía `POST /leads`)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_leads_transicion_estados.py`

## 1. Descripción

Endpoint de administración `PATCH /admin/leads/{lead_id}` que cambia el estado del lead y/o asigna un agente humano, validando la máquina de estados (`recibido → en_revision → cotizado → cerrado`, con `cerrado` alcanzable desde cualquier estado) y que el agente exista. Exige JWT + `is_admin`.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R5 | `PATCH /admin/leads/{id}` para cambiar estado y asignar agente humano | Alta |
| R8 | Transición de estados validada: `recibido → en_revision → cotizado → cerrado` (sin saltos inválidos) | Alta |
| R11 | Los endpoints `/admin/leads*` exigen JWT + `is_admin` (mismo patrón que `backend/routers/admin.py`) | Alta |

## 3. Diseño

**Endpoint (5.2):** `PATCH /admin/leads/{lead_id}` — administración (JWT + `is_admin`).
- Body: `{status?, assigned_agent_id?}`.
- Valida transición de estados y que el agente exista.

**Máquina de estados (5.5):**

```
recibido ──► en_revision ──► cotizado ──► cerrado
   │             │              │
   └─────────────┴──────────────┘ (cerrado puede alcanzarse desde cualquier estado:
                                    lead descartado, cliente no interesado, etc.)
```

- Transiciones válidas: `recibido → en_revision`, `recibido → cerrado`, `en_revision → cotizado`, `en_revision → cerrado`, `cotizado → cerrado`.
- Transiciones inválidas (ej. `recibido → cotizado` sin pasar por `en_revision`, o `cotizado → en_revision`): 400 con detalle.
- `cerrado` es estado terminal: toda transición desde `cerrado` es 400. *(Decisión confirmada: el padre 5.5 declara `cerrado` como estado terminal; toda transición desde `cerrado` es 400.)*

**Formato del 400 de transición inválida:** `detail: "Transición inválida: {estado_actual} -> {estado_solicitado}. Permitidas desde {estado_actual}: {lista}"`. Ejemplo: `"Transición inválida: recibido -> cotizado. Permitidas desde recibido: en_revision, cerrado"`.

## 4. Especificación funcional (SDD)

- **Entrada:** `{status?, assigned_agent_id?}` (al menos uno).
- **Salida:** lead actualizado.
- **Reglas:** transiciones válidas según 5.5; si `assigned_agent_id` se envía, el usuario debe existir (404 si no); al cambiar estado se actualiza `updated_at`.
- **Casos borde:** transición inválida → 400 con detalle de la transición permitida; lead inexistente → 404; body vacío → 422; asignar agente inexistente → 404.

## 5. Criterios de aceptación

- [ ] `PATCH /admin/leads/{id}` cambia estado y asigna agente; las transiciones inválidas devuelven 400.
- [ ] Los endpoints `/admin/leads*` devuelven 401 sin token (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)) y 403 para usuario no admin.
- [ ] El 400 de transición inválida incluye el detalle con el formato `"Transición inválida: {actual} -> {solicitado}. Permitidas desde {actual}: {lista}"`.
- [ ] `cerrado` es estado terminal: toda transición desde `cerrado` devuelve 400 (decisión confirmada con el padre).

## 6. Casos de prueba (TDD Vanilla)

- `test_patch_lead_changes_status_and_assigns_agent`: Arrange: lead `recibido`, agente admin existente. Act: `PATCH /admin/leads/{id}` con `{status:"en_revision", assigned_agent_id: X}`. Assert: 200, estado y agente actualizados.
- `test_patch_lead_rejects_invalid_transition`: Arrange: lead `recibido`. Act: `PATCH` con `{status:"cotizado"}` (salto inválido). Assert: 400 con detalle de transición permitida.
- `test_patch_lead_404_when_agent_not_found`: Arrange: lead existente. Act: `PATCH` con `assigned_agent_id=99999`. Assert: 404.
- `test_patch_lead_closes_from_any_state`: Arrange: leads en `recibido`, `en_revision` y `cotizado`. Act: `PATCH` con `{status:"cerrado"}` en cada uno. Assert: 200 y estado `cerrado`.
- `test_patch_lead_rejects_cotizado_to_en_revision`: Arrange: lead `cotizado`. Act: `PATCH` con `{status:"en_revision"}`. Assert: 400 con detalle de transición permitida.
- `test_patch_lead_rejects_empty_body`: Arrange: lead existente. Act: `PATCH` con `{}`. Assert: 422 (al menos uno de `status`/`assigned_agent_id`).
- `test_patch_lead_404_when_lead_not_found`: Arrange: `lead_id` inexistente. Act: `PATCH` con `{status:"en_revision"}`. Assert: 404.
- `test_patch_lead_requires_auth`: Arrange: sin token. Act: `PATCH /admin/leads/{id}`. Assert: 401 (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_patch_lead_requires_admin`: Arrange: token de usuario normal. Act: `PATCH /admin/leads/{id}`. Assert: 403.
- `test_patch_lead_assigns_agent_without_status_change`: Arrange: lead `recibido`, agente admin existente. Act: `PATCH` con `{assigned_agent_id: X}` (sin `status`). Assert: 200, agente asignado, estado sin cambios.
- `test_patch_lead_updates_updated_at`: Arrange: lead existente. Act: `PATCH` con `{status:"en_revision"}`. Assert: 200 y `updated_at` posterior al valor anterior.

## 7. Riesgos y consideraciones

- **`assigned_agent_id`:** validar que el usuario asignado exista y tenga rol de agente/admin; hoy el modelo solo tiene `is_admin`, por lo que la asignación se limita a admins (extensible a rol `agent` en el futuro).
