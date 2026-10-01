# 004-03 - Ajuste de POST /payments/checkout-session (rechazo de cursos gratuitos)

- **Spec padre:** [004 - Academy: soporte de cursos gratuitos](../../004-academy-cursos-gratuitos.md) (secciones: 5.2, 8.2, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 004-01 (el campo `is_free` en `courses` que valida el checkout)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_academy_checkout_rechaza_gratuitos.py`

## 1. Descripción

Ajuste de defensa en profundidad en `POST /payments/checkout-session`: si `course_id` corresponde a un curso con `is_free=True` → 400 "Este curso es gratuito, inscríbete sin pago", antes de tocar Stripe o `PRICE_MAP`. Los cursos de pago mantienen el comportamiento actual.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R5 | `POST /payments/checkout-session` rechaza cursos gratuitos con 400 | Alta |

## 3. Diseño

**Endpoint (5.2):** `POST /payments/checkout-session` — JWT (según el padre).
- Si `course_id` corresponde a un curso con `is_free=True` → 400 "Este curso es gratuito, inscríbete sin pago".

**Comportamiento real verificado en código (`backend/routers/payments.py`, `backend/services/stripe.py`, `backend/schemas.py`):**
- El endpoint actual NO declara dependencia JWT (el padre la exige; discrepancia confirmada — la corrección queda asignada a la spec 007(k), ver 7).
- `CheckoutSessionRequest.course_id` está tipado como el enum `CourseId` (3 valores: `plc-industrial`, `scada-redes`, `robotica-industrial`); un `course_id` fuera del enum → 422 (validación Pydantic) antes de llegar a la lógica.
- `create_checkout_session` usa `PRICE_MAP` (mismo `STRIPE_PRICE_ID` para los 3 cursos, riesgo #13) y, en modo mock (`payments_mock`), crea el purchase y el enrollment directamente sin llamar a Stripe.
- El chequeo de `is_free` de esta spec debe ocurrir antes de cualquier llamada a Stripe o `PRICE_MAP`.

## 4. Especificación funcional (SDD)

- **Entrada:** payload existente `{course_id, ...}`.
- **Salida:** 400 si el curso es gratuito (antes de tocar Stripe).
- **Reglas:** el chequeo de `is_free` ocurre antes de cualquier llamada a Stripe o `PRICE_MAP`.
- **Dependencia con 007(d):** el rechazo 400 por `is_free` solo es alcanzable hoy para los 3 cursos del seed si se vuelven gratuitos (el enum `CourseId` bloquea cualquier otro `course_id` con 422). Tras 007(d) (`course_id: str` validado contra BD), el chequeo aplica a cualquier curso, incluidos los creados por admin (005).
- **Casos borde:** curso gratuito → 400; curso de pago → comportamiento actual sin cambios; curso inexistente → hoy 422 (el enum rechaza el valor antes de la lógica) y tras 007(d) 404 (validación contra BD).

## 5. Criterios de aceptación

- [ ] `POST /payments/checkout-session` devuelve 400 para curso gratuito, sin llamar a Stripe ni a `PRICE_MAP`.
- [ ] Los cursos de pago mantienen el comportamiento actual (regresión: sigue creando la sesión).
- [ ] El caso de curso inexistente queda cubierto según el estado del enum: 422 hoy (fuera del enum `CourseId`) y 404 tras 007(d).

## 6. Casos de prueba (TDD Vanilla)

- `test_checkout_session_rejects_free_course`: Arrange: curso `is_free=True`, usuario autenticado. Act: `POST /payments/checkout-session` con ese curso. Assert: 400 y **no** se llama a Stripe (mock verifica ausencia de llamada).
- `test_checkout_session_paid_course_unchanged`: Arrange: curso de pago. Act: `POST /payments/checkout-session`. Assert: comportamiento actual (200 con session id o mock).
- `test_checkout_session_unknown_course_422_today_404_after_007d`: Arrange: `course_id` inexistente (fuera del enum `CourseId`). Act: `POST /payments/checkout-session`. Assert: hoy 422 (validación del enum); tras 007(d) el caso pasa a 404 (validación contra BD). El test se actualiza cuando se implemente 007(d).

## 7. Riesgos y consideraciones

- **`STRIPE_PRICE_ID`:** un curso gratuito no necesita precio de Stripe; `PRICE_MAP` (riesgo #13) no debe consultarse para cursos gratuitos.
- **Limitación preexistente del enum `CourseId` (nuevo hallazgo):** `CheckoutSessionRequest.course_id` está tipado como el enum `CourseId` (`schemas.py`), que solo admite los 3 cursos del seed (`plc-industrial`, `scada-redes`, `robotica-industrial`). Un curso nuevo creado por admin (005) ni siquiera llega al checkout (422 por enum). Esto significa: (a) el rechazo 400 por `is_free` de esta spec solo es alcanzable hoy para los 3 cursos del seed si se vuelven gratuitos; (b) la corrección completa (enum → `str` validado contra BD, y `Purchase.course_id` de `SqlEnum(CourseId)` a `String`) queda asignada a la spec 007(d), que es prerequisito real para vender cualquier curso nuevo, no solo para unificar catálogos.
- **Discrepancia de autenticación (confirmada):** el padre declara `POST /payments/checkout-session` como JWT, pero el código actual no declara dependencia de autenticación. Decisión confirmada: el endpoint DEBE exigir JWT (`Depends(get_current_user_id)`); la corrección queda asignada a la spec 007(k). Esta spec no introduce ni elimina autenticación.
