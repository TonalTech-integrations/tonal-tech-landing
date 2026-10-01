pere# 004 - Academy: soporte de cursos gratuitos (is_free en cursos, inscripción sin checkout)

- **Estado:** borrador
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

La visión (FUNCIONALIDAD.md) pide que Academy funcione "similar a Udemy": cursos **gratuitos o de pago**, usando Stripe para los de pago. Hoy el backend solo soporta `is_free` a nivel de **lección** (`backend/services/persistence.py`, columna `is_free` en `lessons`; `schemas.py`), y **todos** los cursos pasan por Stripe Checkout (gap Parcial, V8 del spec 001).

Esta spec agrega el concepto de **curso gratuito completo**: campo `is_free` en la tabla `courses`, flujo de inscripción sin checkout (enrollment automático al hacer clic en "Inscribirme gratis"), ajustes en `GET /courses`, `GET /courses/{id}`, `POST /payments/checkout-session` (rechazar cursos gratuitos) y la UI en `AcademyPage`/`CourseViewer`.

## 2. Objetivos

- Agregar `is_free` a nivel de curso (no solo de lección).
- Permitir inscripción automática a cursos gratuitos sin pasar por Stripe.
- Rechazar el checkout para cursos gratuitos en el backend (defensa en profundidad).
- Mostrar el estado correcto en la UI: botón "Inscribirme gratis" vs botón de compra.
- Mantener la compatibilidad con lecciones de muestra: si un curso es gratuito, todas sus lecciones quedan accesibles al inscribirse; el `is_free` de **lección** sigue aplicando solo en cursos de pago (lecciones de muestra sin inscripción).

## 3. Alcance

### Incluye
- Migración: columna `is_free` (bool, default `False`) en `courses` + actualización de `COURSE_SEED` (al menos 1 curso gratuito de ejemplo).
- Ajustes en schemas: `CourseSummary` y `CourseDetailResponse` exponen `is_free`.
- Endpoint `POST /courses/{course_id}/enroll-free` (autenticado, idempotente).
- Ajuste en `POST /payments/checkout-session`: 400 si el curso es gratuito.
- UI: `AcademyPage`/`CourseViewer` con botón "Inscribirme gratis" y flujo de inscripción.
- Especificación SDD + casos TDD Vanilla.

### Excluye
- Cursos "freemium" (parte gratis, parte pago) — el `is_free` de lección ya cubre muestras dentro de cursos de pago.
- Cupones/descuentos.
- Cambios en el flujo de pago de cursos de pago (Stripe Checkout se mantiene).
- Gestión del tipo pago/gratuito desde el dashboard admin (lo cubre la spec 005; aquí solo el modelo y el flujo de inscripción).

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | La tabla `courses` tiene `is_free` (bool, default `False`) | Alta |
| R2 | `GET /courses` y `GET /courses/{id}` exponen `is_free` en la respuesta | Alta |
| R3 | `POST /courses/{course_id}/enroll-free` (JWT) inscribe al usuario sin pago | Alta |
| R4 | El enroll-free es idempotente: si ya está inscrito, responde 200 sin duplicar | Alta |
| R5 | `POST /payments/checkout-session` rechaza cursos gratuitos con 400 | Alta |
| R6 | Un curso gratuito no requiere `STRIPE_PRICE_ID` para inscribirse | Media |
| R7 | `CourseViewer` muestra "Inscribirme gratis" para cursos gratuitos no inscritos | Alta |
| R8 | Si el usuario no está autenticado y hace clic en "Inscribirme gratis", se pide login (patrón existente de compra) | Alta |
| R9 | Tras inscribirse, el curso se refresca con `enrolled=true` y se desbloquean las lecciones | Alta |
| R10 | El seed incluye al menos un curso gratuito de ejemplo | Media |
| R11 | Regla de coherencia: `is_free=True` ⇒ `price_cents=0` (y viceversa) | Media |

## 5. Diseño / Arquitectura

### 5.1 Modelo de datos (backend/services/persistence.py)

- **Tabla `courses`:** nueva columna `is_free` (Boolean, default `False`, no nula).
- **`COURSE_SEED`:** agregar `is_free` a cada curso; al menos uno con `is_free=True` (ej. un curso introductorio).
- **Regla de coherencia `is_free <-> price_cents` (R11):** `is_free=True` ⇒ `price_cents=0` (y viceversa). La validación de esta regla en el formulario/endpoint admin de cursos queda diferida a la spec 005 (005 R12).
- **Regla de negocio de acceso:** para un curso con `is_free=True`, `has_access = usuario autenticado AND tiene enrollment` (igual que un curso pagado con enrollment). La diferencia es **cómo se obtiene el enrollment**: automático (enroll-free) en lugar de compra.
- El `is_free` de **lección** se mantiene: en cursos de pago permite lecciones de muestra sin inscripción; en cursos gratuitos es irrelevante (todas accesibles con enrollment).

### 5.2 Endpoints

| Método | Ruta | Autenticación | Descripción |
|--------|------|---------------|-------------|
| POST | `/courses/{course_id}/enroll-free` | JWT | Inscribe al usuario al curso gratuito. 404 si el curso no existe/inactivo; 400 si el curso no es gratuito; 200 si ya estaba inscrito (idempotente); 201 en la primera inscripción |
| GET | `/courses` | Opcional | `CourseSummary` incluye `is_free` |
| GET | `/courses/{course_id}` | Opcional | `CourseDetailResponse` incluye `is_free` |
| POST | `/payments/checkout-session` | JWT | Si `course_id` corresponde a un curso con `is_free=True` → 400 "Este curso es gratuito, inscríbete sin pago" |

- El enroll-free reutiliza `grant_enrollment(user_id, course_id, source="free")` de `backend/services/persistence.py` (la función base que ya usan `grant_enrollment_from_purchase` y `grant_enrollment_by_email`): el `user_id` viene directo del JWT, sin lookup por email. **Nota de concurrencia (riesgo #12):** `grant_enrollment` actual es check-then-insert (verifica `existing` y luego inserta), idempotente en secuencial pero **no** segura bajo concurrencia: dos peticiones simultáneas pueden pasar ambas el check y la segunda revienta contra el `UniqueConstraint` de `enrollments`. El endpoint debe capturar la excepción de integridad y responder 200 (idempotente); se agregan pruebas.

### 5.3 Frontend (components/academy/academy-page.tsx, course-viewer.tsx)

- **`AcademyPage`:** al recibir el catálogo, cada tarjeta muestra "Gratis" si `course.is_free` (además del precio si es de pago).
- **`CourseViewer`:** en el panel de compra:
  - Si `course.is_free && !course.enrolled && isAuthed` → botón **"Inscribirme gratis"** → llama `enrollFree(course.id)` (nueva función en `lib/api.ts`) → al éxito, refresca el curso (`getCourseDetail(course.id)`, función existente en `lib/api.ts`) para que `enrolled=true` y las lecciones se desbloqueen.
  - Si `course.is_free && !course.enrolled && !isAuthed` → clic en "Inscribirme gratis" → `onRequireLogin` (mismo patrón que el botón de compra).
  - Si `course.enrolled` → no se muestra panel de compra (comportamiento existente).
  - Si `!course.is_free` → botón de compra actual (sin cambios).
- **`lib/api.ts`:** añadir `enrollFree(courseId): Promise<void>` (requiere JWT).

### 5.4 Flujo de inscripción gratuita

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

## 6. Criterios de aceptación

- [ ] `courses.is_free` existe con default `False` y el seed tiene al menos un curso gratuito.
- [ ] `GET /courses` y `GET /courses/{id}` incluyen `is_free`.
- [ ] `POST /courses/{id}/enroll-free` inscribe al usuario; la segunda llamada responde 200 sin duplicar el enrollment.
- [ ] `POST /courses/{id}/enroll-free` devuelve 400 para curso de pago y 404 para curso inexistente/inactivo.
- [ ] `POST /payments/checkout-session` devuelve 400 para curso gratuito.
- [ ] `CourseViewer` muestra "Inscribirme gratis" solo para cursos gratuitos no inscritos; pide login si no hay sesión.
- [ ] Tras inscribirse, el curso se refresca con `enrolled=true` y las lecciones quedan accesibles.
- [ ] Existen pruebas de concurrencia para enroll-free (dos llamadas simultáneas → un solo enrollment).

## 7. Riesgos y consideraciones

- **Concurrencia/idempotencia:** dos clics simultáneos en "Inscribirme gratis" pueden disparar dos inserts; el `UniqueConstraint` de `enrollments` mitiga duplicados, pero el endpoint debe capturar la excepción de integridad y responder 200 (idempotente). Se agregan pruebas (riesgo #12).
- **Migración de BD:** agregar columna con default no rompe filas existentes; el seed debe actualizarse. Si se usa SQLite en desarrollo, la migración es recreación de tablas (patrón existente del proyecto).
- **`STRIPE_PRICE_ID`:** un curso gratuito no necesita precio de Stripe; `PRICE_MAP` (riesgo #13) no debe consultarse para cursos gratuitos.
- **UI engañosa:** evitar mostrar "Gratis" y botón de compra a la vez; el estado `is_free` debe ser consistente entre catálogo y detalle (misma fuente: backend).
- **Limitación preexistente del enum `CourseId` (nuevo hallazgo):** `CheckoutSessionRequest.course_id` está tipado como el enum `CourseId` (`schemas.py`), que solo admite los 3 cursos del seed (`plc-industrial`, `scada-redes`, `robotica-industrial`). Un curso nuevo creado por admin (005) ni siquiera llega al checkout (422 por enum). Esto significa: (a) el rechazo 400 por `is_free` de esta spec solo es alcanzable hoy para los 3 cursos del seed si se vuelven gratuitos; (b) la corrección completa (enum → `str` validado contra BD, y `Purchase.course_id` de `SqlEnum(CourseId)` a `String`) queda asignada a la spec 007(d), que es prerequisito real para vender cualquier curso nuevo, no solo para unificar catálogos.
- **Dependencia con 007(d):** la landing pública (`AcademySection` con `lib/products.ts`) seguirá mostrando el catálogo viejo hasta que se unifiquen catálogos; el flujo gratuito completo solo es visible en `/academy` hasta entonces.
- **Autenticación en `POST /payments/checkout-session` (deuda a cerrar):** el padre exige JWT, pero el código actual no lo declara. Decisión confirmada: el endpoint DEBE exigir JWT (`Depends(get_current_user_id)`); la corrección queda asignada a la spec 007(k) (`docs/specs/007-endurecimiento-seguridad.md`).

## 8. Especificación funcional (SDD)

### 8.1 `POST /courses/{course_id}/enroll-free` (JWT)

- **Entrada:** `course_id` (str) en path; token JWT en header.
- **Salida:** 201 `{enrolled: true}` (primera inscripción) o 200 `{enrolled: true, already_enrolled: true}` (idempotente).
- **Reglas de negocio:**
  - Curso inexistente o `is_active=False` → 404 "Curso no encontrado".
  - Curso con `is_free=False` → 400 "Este curso no es gratuito".
  - Crea el enrollment con el mismo mecanismo que una compra (misma tabla, mismo `UniqueConstraint`).
  - Si el enrollment ya existe → 200 sin error (idempotente).
  - Si dos peticiones concurrentes intentan crear el mismo enrollment → una gana, la otra captura la excepción de integridad y responde 200.
- **Casos borde:** usuario no autenticado → 401 (`HTTPBearer` de FastAPI sin credenciales responde 401 "Not authenticated" (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima); token inválido/expirado → 401, que es lo que lanza `get_current_user_id`); curso gratuito ya inscrito → 200; curso gratuito inactivo → 404; `course_id` inexistente → 404.

### 8.2 `POST /payments/checkout-session` (ajuste)

- **Entrada:** payload existente `{course_id, ...}` + token JWT (obligatorio).
- **Salida:** 400 si el curso es gratuito (antes de tocar Stripe).
- **Reglas:** el endpoint exige JWT (`get_current_user_id`); sin token → 401 (`HTTPBearer` sin credenciales), token inválido/expirado → 401; el chequeo de `is_free` ocurre antes de cualquier llamada a Stripe o `PRICE_MAP`.
- **Deuda a cerrar (007):** el código actual de `POST /payments/checkout-session` NO declara la dependencia JWT (verificado en `backend/routers/payments.py`). Decisión confirmada: el endpoint DEBE exigir JWT; la corrección queda asignada a la spec 007(k) (`docs/specs/007-endurecimiento-seguridad.md`).
- **Casos borde:** curso gratuito → 400; curso de pago → comportamiento actual sin cambios; curso inexistente → 404 (comportamiento actual); sin token → 401; token inválido → 401.

### 8.3 `CourseViewer` (frontend)

- **Entrada:** `course` (con `is_free`, `enrolled`), `isAuthed`, callbacks existentes.
- **Salida:** panel de compra con botón correcto según estado.
- **Reglas:** `is_free && !enrolled && isAuthed` → "Inscribirme gratis" (llama `enrollFree`); `is_free && !enrolled && !isAuthed` → clic pide login; `enrolled` → sin panel; `!is_free` → botón de compra actual.
- **Casos borde:** error de red en `enrollFree` → mensaje de error sin cerrar el panel; doble clic → deshabilitar botón durante la llamada; refresco del curso falla tras inscribirse → mostrar error y permitir reintento.

## 9. Casos de prueba (TDD Vanilla)

- `test_enroll_free_creates_enrollment_for_free_course`: Arrange: curso `is_free=True`, usuario autenticado sin enrollment. Act: `POST /courses/{id}/enroll-free`. Assert: 201, enrollment creado.
- `test_enroll_free_is_idempotent`: Arrange: usuario ya inscrito. Act: `POST /courses/{id}/enroll-free`. Assert: 200 con `already_enrolled=true`, un solo enrollment en BD.
- `test_enroll_free_rejects_paid_course`: Arrange: curso `is_free=False`. Act: `POST /courses/{id}/enroll-free`. Assert: 400 "Este curso no es gratuito".
- `test_enroll_free_404_for_unknown_course`: Arrange: `course_id` inexistente. Act: endpoint. Assert: 404.
- `test_enroll_free_404_for_inactive_course`: Arrange: curso `is_active=False`. Act: endpoint. Assert: 404.
- `test_enroll_free_requires_auth`: Arrange: sin token. Act: `POST /courses/{id}/enroll-free`. Assert: 401 (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_enroll_free_concurrent_requests_create_single_enrollment`: Arrange: curso gratuito, usuario sin enrollment. Act: dos `POST /courses/{id}/enroll-free` simultáneos. Assert: un solo enrollment en BD y ambas respuestas 2xx (201/200).
- `test_course_list_includes_is_free_flag`: Arrange: curso gratuito y curso de pago. Act: `GET /courses`. Assert: cada `CourseSummary` incluye `is_free` correcto.
- `test_course_detail_includes_is_free_flag`: Arrange: curso gratuito. Act: `GET /courses/{id}`. Assert: `is_free=True` en la respuesta.
- `test_checkout_session_rejects_free_course`: Arrange: curso `is_free=True`, usuario autenticado. Act: `POST /payments/checkout-session` con ese curso. Assert: 400 y **no** se llama a Stripe (mock verifica ausencia de llamada).
- `test_checkout_session_paid_course_unchanged`: Arrange: curso de pago. Act: `POST /payments/checkout-session`. Assert: comportamiento actual (200 con session id o mock).
- `test_course_viewer_shows_enroll_free_button_when_free_and_not_enrolled`: Arrange: `course.is_free=true`, `enrolled=false`, `isAuthed=true`. Act: render. Assert: botón "Inscribirme gratis" presente, sin botón de compra.
- `test_course_viewer_enroll_free_requires_login_when_unauthenticated`: Arrange: `is_free=true`, `enrolled=false`, `isAuthed=false`. Act: clic en "Inscribirme gratis". Assert: `onRequireLogin` invocado, `enrollFree` no invocado.
- `test_course_viewer_hides_purchase_panel_when_enrolled`: Arrange: `enrolled=true` (curso gratuito). Act: render. Assert: sin panel de compra ni botón de inscripción.
- `test_course_viewer_refreshes_course_after_enroll_free_success`: Arrange: mock de `enrollFree` resolviendo. Act: clic en "Inscribirme gratis". Assert: `getCourseDetail` (función existente en `lib/api.ts`) invocado para refrescar y el curso pasa a `enrolled=true`.
- `test_course_viewer_shows_error_when_enroll_free_fails`: Arrange: mock de `enrollFree` rechazando. Act: clic. Assert: mensaje de error visible, panel sigue abierto.
- `test_course_viewer_disables_enroll_button_while_loading`: Arrange: mock de `enrollFree` con promesa pendiente. Act: clic y doble clic. Assert: botón deshabilitado, `enrollFree` invocado una sola vez.
