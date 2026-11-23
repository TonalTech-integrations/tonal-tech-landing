# 002-06 - Consultar cotización (GET /admin/leads/{id}/quote)

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.1, 5.2, 6)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 002-05 (la cotización consultada se crea vía `POST /admin/leads/{id}/quote`)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_leads_consultar_cotizacion.py`

## 1. Descripción

Endpoint de administración `GET /admin/leads/{lead_id}/quote` que devuelve la cotización de un lead o 404 si no existe. Exige JWT + `is_admin`.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R7 | `GET /admin/leads/{id}/quote` para consultar la cotización del lead | Media |
| R11 | Los endpoints `/admin/leads*` exigen JWT + `is_admin` (mismo patrón que `backend/routers/admin.py`) | Alta |

## 3. Diseño

**Endpoint (5.2):** `GET /admin/leads/{lead_id}/quote` — administración (JWT + `is_admin`).
- Descripción: devuelve la cotización o 404 si no existe.

**Modelo relacionado (5.1):** tabla `quotes` (1 cotización activa por lead).

## 4. Especificación funcional (SDD)

- **Entrada:** `lead_id` (int) en path; token JWT + `is_admin`.
- **Salida:** la cotización del lead: `{id, lead_id, amount_cents, currency, valid_until, notes, created_by, created_at}` (campos de la tabla `quotes`, 5.1), o 404 si no existe.
- **Reglas:** solo admins; 404 si la cotización no existe (5.2). El `detail` del 404 distingue ambos casos: `"Lead no encontrado"` si el lead no existe, `"Cotización no encontrada"` si el lead existe pero no tiene cotización.
- **Casos borde:** lead inexistente → 404 con `detail: "Lead no encontrado"`; lead sin cotización → 404 con `detail: "Cotización no encontrada"`.

## 5. Criterios de aceptación

- [ ] Los endpoints `/admin/leads*` devuelven 401 sin token (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)) y 403 para usuario no admin.
- [ ] `GET /admin/leads/{id}/quote` devuelve la cotización del lead; 404 con `detail` distinto si el lead no existe (`"Lead no encontrado"`) vs. si no tiene cotización (`"Cotización no encontrada"`).

## 6. Casos de prueba (TDD Vanilla)

- `test_get_quote_returns_quote`: Arrange: lead con cotización creada (002-05). Act: `GET /admin/leads/{id}/quote`. Assert: 200 con la cotización (`amount_cents`, `currency`, `valid_until`, `notes`).
- `test_get_quote_404_when_lead_not_found`: Arrange: `lead_id` inexistente. Act: `GET /admin/leads/{id}/quote`. Assert: 404 con `detail: "Lead no encontrado"`.
- `test_get_quote_404_when_no_quote`: Arrange: lead sin cotización. Act: `GET /admin/leads/{id}/quote`. Assert: 404 con `detail: "Cotización no encontrada"`.
- `test_get_quote_requires_auth`: Arrange: sin token. Act: `GET /admin/leads/{id}/quote`. Assert: 401 (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_get_quote_requires_admin`: Arrange: token de usuario normal. Act: `GET /admin/leads/{id}/quote`. Assert: 403.

## 7. Riesgos y consideraciones

- **Dependencia con 002-05:** el endpoint solo devuelve datos si la cotización fue creada; el dashboard (005) debe distinguir el 404 de lead inexistente del de cotización inexistente (en el segundo caso mostrar "Crear cotización", según 005, sección 8.4).
