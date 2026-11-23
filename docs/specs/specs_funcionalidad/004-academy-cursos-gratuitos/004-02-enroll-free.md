# 004-02 - Inscripción gratuita (POST /courses/{id}/enroll-free)

- **Spec padre:** [004 - Academy: soporte de cursos gratuitos](../../004-academy-cursos-gratuitos.md) (secciones: 5.2, 5.4, 8.1, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 004-01 (el campo `is_free` en `courses` que valida el endpoint)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_academy_enroll_free.py`

## 1. Descripción

Endpoint autenticado `POST /courses/{course_id}/enroll-free` que inscribe al usuario en un curso gratuito sin pasar por Stripe: 201 en la primera inscripción, 200 idempotente si ya estaba inscrito, 400 si el curso no es gratuito y 404 si no existe/inactivo. Reutiliza `grant_enrollment(user_id, course_id, source="free")` y debe capturar la excepción de integridad bajo concurrencia (riesgo #12).

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R3 | `POST /courses/{course_id}/enroll-free` (JWT) inscribe al usuario sin pago | Alta |
| R4 | El enroll-free es idempotente: si ya está inscrito, responde 200 sin duplicar | Alta |

## 3. Diseño

**Endpoint (5.2):** `POST /courses/{course_id}/enroll-free` — JWT.
- 404 si el curso no existe/inactivo; 400 si el curso no es gratuito; 200 si ya estaba inscrito (idempotente); 201 en la primera inscripción.

**Implementación (5.2):** el enroll-free reutiliza `grant_enrollment(user_id, course_id, source="free")` de `backend/services/persistence.py`. **Verificado en código:** la función YA existe con firma `grant_enrollment(user_id: int, course_id: str, source: str = "purchase")` — el default actual es `"purchase"`; el endpoint de esta spec pasa explícitamente `source="free"` para distinguir inscripciones gratuitas de compras. Es la función base que ya usan `grant_enrollment_from_purchase` y `grant_enrollment_by_email`: el `user_id` viene directo del JWT, sin lookup por email. **Nota de concurrencia (riesgo #12 de docs/ANALISIS-PROYECTO.md, falta de tests de concurrencia en `grant_enrollment`):** `grant_enrollment` actual es check-then-insert (verifica `existing` y luego inserta), idempotente en secuencial pero **no** segura bajo concurrencia: dos peticiones simultáneas pueden pasar ambas el check y la segunda revienta contra el `UniqueConstraint` de `enrollments`. El endpoint debe capturar la excepción de integridad y responder 200 (idempotente); se agregan pruebas.

**Flujo (5.4):**

```
Usuario autenticado ve curso is_free=True, enrolled=False
        │
        ▼
Clic "Inscribirme gratis" ──► POST /courses/{id}/enroll-free
        │                              │
        │ 201/200 (idempotente)        │ 400 (no gratuito) / 404 (no existe)
        ▼                              ▼
Refrescar curso (enrolled=true)   Mostrar error
        │
        ▼
Lecciones desbloqueadas (has_access=true)
```

## 4. Especificación funcional (SDD)

- **Entrada:** `course_id` (str) en path; token JWT en header.
- **Salida:** 201 `{enrolled: true}` (primera inscripción) o 200 `{enrolled: true, already_enrolled: true}` (idempotente).
- **Reglas de negocio:**
  - Curso inexistente o `is_active=False` → 404 "Curso no encontrado".
  - Curso con `is_free=False` → 400 "Este curso no es gratuito".
  - Crea el enrollment con el mismo mecanismo que una compra (misma tabla, mismo `UniqueConstraint`).
  - Si el enrollment ya existe → 200 sin error (idempotente).
  - Si dos peticiones concurrentes intentan crear el mismo enrollment → una gana, la otra captura la excepción de integridad y responde 200.
- **Casos borde:** usuario no autenticado → 401 (`HTTPBearer` de FastAPI sin credenciales responde 401 "Not authenticated" (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima); token inválido/expirado → 401, que es lo que lanza `get_current_user_id`); curso gratuito ya inscrito → 200; curso gratuito inactivo → 404; `course_id` inexistente → 404.

## 5. Criterios de aceptación

- [ ] `POST /courses/{id}/enroll-free` inscribe al usuario; la segunda llamada responde 200 sin duplicar el enrollment.
- [ ] `POST /courses/{id}/enroll-free` devuelve 400 para curso de pago y 404 para curso inexistente/inactivo.
- [ ] Existen pruebas de concurrencia para enroll-free (dos llamadas simultáneas → un solo enrollment).

## 6. Casos de prueba (TDD Vanilla)

- `test_enroll_free_creates_enrollment_for_free_course`: Arrange: curso `is_free=True`, usuario autenticado sin enrollment. Act: `POST /courses/{id}/enroll-free`. Assert: 201, enrollment creado.
- `test_enroll_free_is_idempotent`: Arrange: usuario ya inscrito. Act: `POST /courses/{id}/enroll-free`. Assert: 200 con `already_enrolled=true`, un solo enrollment en BD.
- `test_enroll_free_rejects_paid_course`: Arrange: curso `is_free=False`. Act: `POST /courses/{id}/enroll-free`. Assert: 400 "Este curso no es gratuito".
- `test_enroll_free_404_for_unknown_course`: Arrange: `course_id` inexistente. Act: endpoint. Assert: 404.
- `test_enroll_free_404_for_inactive_course`: Arrange: curso `is_active=False`. Act: endpoint. Assert: 404.
- `test_enroll_free_requires_auth`: Arrange: sin token. Act: `POST /courses/{id}/enroll-free`. Assert: 401 (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_enroll_free_concurrent_requests_create_single_enrollment`: Arrange: curso gratuito, usuario sin enrollment. Act: dos `POST /courses/{id}/enroll-free` simultáneos. Assert: un solo enrollment en BD y ambas respuestas 2xx (201/200).
- `test_enroll_free_rejects_invalid_token`: Arrange: curso `is_free=True`, token inválido/expirado. Act: `POST /courses/{id}/enroll-free` con `Authorization: Bearer <token inválido>`. Assert: 401 (lo lanza `get_current_user_id`).
- `test_enroll_free_keeps_previous_lesson_access`: Arrange: curso gratuito con una lección `is_free=True` (muestra) y una lección de pago; usuario sin enrollment. Act: `GET /courses/{id}` antes y después de `POST /courses/{id}/enroll-free`. Assert: la lección muestra tenía `has_access=True` antes y sigue `True` después; la lección no gratuita pasa de `False` a `True` tras inscribirse (el enroll-free no revierte accesos previos).

## 7. Riesgos y consideraciones

- **Concurrencia/idempotencia (riesgo #12 de docs/ANALISIS-PROYECTO.md, falta de tests de concurrencia en `grant_enrollment`):** dos clics simultáneos en "Inscribirme gratis" pueden disparar dos inserts; el `UniqueConstraint` de `enrollments` mitiga duplicados, pero el endpoint debe capturar la excepción de integridad y responder 200 (idempotente). Se agregan pruebas.
