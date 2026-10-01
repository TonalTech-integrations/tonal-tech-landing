# Análisis Completo del Proyecto — Tonal-Tech Landing

> Metodología aplicada: **SDD (Specification-Driven Development)** — se define la especificación de cada servicio/componente/funcionalidad (propósito, entradas, salidas, reglas de negocio y casos borde) **antes** de derivar pruebas — y **TDD Vanilla** — casos de prueba unitarios simples, sin frameworks BDD, descritos en formato **Arrange / Act / Assert (AAA)**.
>
> Este documento se basa exclusivamente en el código fuente existente en el repositorio `tonal-tech-landing`. No se ha inventado funcionalidad no presente en el código. Los nombres de variables sensibles (API keys, secretos, credenciales) se mencionan únicamente por su nombre de variable de entorno, nunca por su valor.

---

## 1. Resumen ejecutivo

**Tonal-Tech Landing** es una aplicación fullstack compuesta por:

- **Frontend** (`app/`, `components/`, `lib/`): sitio Next.js 16 (App Router) con exportación estática (`output: "export"`) para publicarse en GitHub Pages bajo el basePath `/tonal-tech-landing`. Contiene:
  - Una **landing comercial B2B** (página `/`) con formulario de leads, catálogo de servicios y sección de "Academy" promocional (con datos estáticos y checkout simulado vía panel de leads, sin backend real).
  - Una **plataforma de e-learning real** ("Tonal-Tech Academy", ruta `/academy`) con registro/login, catálogo de cursos, reproductor de video con progreso, compra vía Stripe Checkout y página de confirmación de pago (`/success`).
- **Backend** (`backend/`): servicio FastAPI (Python 3.11+) que expone:
  - Autenticación de usuarios con JWT (registro, login, perfil).
  - Catálogo de cursos, módulos y lecciones con control de acceso (lecciones gratuitas vs. de pago) y seguimiento de progreso por usuario.
  - Integración con **Stripe** (Checkout Sessions y webhooks) para la venta de cursos, incluyendo un **modo simulado** (`PAYMENTS_MOCK`) que evita llamadas reales a Stripe.
  - Integración con **AWS S3** para generar URLs pre-firmadas de subida y descarga/streaming de videos de las lecciones.
  - Persistencia en **PostgreSQL** (o SQLite en desarrollo) vía SQLAlchemy, con un modelo de datos de usuarios, cursos, módulos, lecciones, inscripciones (enrollments), progreso de lecciones y compras (purchases).
  - Un panel de **administración** (endpoints `/admin/*`) protegido por rol `is_admin` para gestionar cursos, módulos, lecciones e inscripciones manuales.
- **Infraestructura**: contenedores Docker/Podman independientes para frontend (`Dockerfile.frontend`) y backend (`backend/Dockerfile`), orquestados con `podman-compose.yml`; despliegue automático del frontend estático a GitHub Pages vía GitHub Actions (`.github/workflows/deploy.yml`).

Existen **dos catálogos de cursos distintos y desacoplados** en el código actual:
1. `lib/products.ts` (frontend, hardcodeado) — usado por la landing pública (`components/academy-section.tsx`, `components/course-detail.tsx`), con IDs `plc-industrial`, `scada-networks`, `robotics`. No se conecta al backend; el "checkout" solo abre el panel de leads.
2. El catálogo real servido por el backend (`backend/services/persistence.py`, tabla `courses`), usado por `/academy` a través de `lib/api.ts`, con IDs `plc-industrial`, `scada-redes`, `robotica-industrial`. Este es el que efectivamente procesa pagos y videos.

Esta duplicación es una **deuda técnica relevante** documentada en la sección 6.

---

## 2. Arquitectura general (diagrama textual)

```
                              ┌───────────────────────────────────────────┐
                              │              USUARIO / NAVEGADOR            │
                              └───────────────────────────────────────────┘
                                         │                        │
                          (1) Landing pública           (2) Academy real
                                         │                        │
                                         ▼                        ▼
                       ┌───────────────────────────────────────────────────┐
                       │        FRONTEND — Next.js 16 (export estático)      │
                       │  app/page.tsx            app/academy/page.tsx       │
                       │  app/success/page.tsx                               │
                       │                                                     │
                       │  components/*  (landing, lead-panel, academy/*)     │
                       │  lib/api.ts  (cliente HTTP hacia backend)           │
                       │  lib/products.ts, lib/tonal-data.ts (datos estáticos)│
                       └───────────────────────────────────────────────────┘
                                         │
                                (fetch HTTP JSON, JWT Bearer)
                                         │
                                         ▼
                       ┌───────────────────────────────────────────────────┐
                       │           BACKEND — FastAPI (backend/main.py)       │
                       │  routers: auth, courses, payments, videos, admin    │
                       │  services: stripe.py, storage.py, persistence.py    │
                       │  CORS configurado vía CORS_ORIGINS                  │
                       └───────────────────────────────────────────────────┘
                              │                 │                   │
                              ▼                 ▼                   ▼
                     ┌────────────────┐ ┌───────────────┐  ┌──────────────────┐
                     │   PostgreSQL   │ │  Stripe API    │  │     AWS S3        │
                     │ (o SQLite dev) │ │ (Checkout +    │  │ (presigned URLs   │
                     │ usuarios,      │ │  Webhooks)     │  │  de subida y      │
                     │ cursos,        │ │                │  │  descarga/stream  │
                     │ enrollments,   │ │                │  │  de video)        │
                     │ progreso,      │ │                │  │                   │
                     │ compras        │ │                │  │                   │
                     └────────────────┘ └───────────────┘  └──────────────────┘

  Infra: Dockerfile.frontend + backend/Dockerfile orquestados con podman-compose.yml
  CI/CD: .github/workflows/deploy.yml -> build estático -> GitHub Pages
```

---

## 3. Backend — Especificaciones (SDD) y casos de prueba (TDD Vanilla)

### 3.0 Configuración (`backend/config.py`)

**Especificación**
- Carga configuración desde variables de entorno (o `.env`) usando `pydantic-settings`.
- Variables obligatorias (sin default): `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`.
- Variables con default: `AWS_REGION` (`us-east-1`), `CORS_ORIGINS` (`http://localhost:3000`), `DATABASE_URL` (SQLite/Postgres local), `APP_URL`, `PAYMENTS_MOCK` (`False`), `JWT_SECRET_KEY`, `JWT_ALGORITHM` (`HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (1440).
- `get_cors_origins()` transforma la cadena `CORS_ORIGINS` (separada por comas) en una lista, ignorando entradas vacías.
- Si falta una variable obligatoria, la aplicación debe fallar al arrancar (validación de pydantic).

**Casos de prueba (AAA)**
- `test_get_cors_origins_parses_comma_separated_list`: Arrange: crear `Settings` con `cors_origins="http://a.com, http://b.com"`. Act: llamar `get_cors_origins()`. Assert: retorna `["http://a.com", "http://b.com"]` sin espacios.
- `test_get_cors_origins_ignores_empty_entries`: Arrange: `cors_origins="http://a.com,,"`. Act: `get_cors_origins()`. Assert: no incluye cadenas vacías.
- `test_settings_raises_when_required_var_missing`: Arrange: entorno sin `STRIPE_SECRET_KEY`. Act: instanciar `Settings()`. Assert: se lanza `ValidationError`.
- `test_settings_uses_default_payments_mock_false`: Arrange: entorno con solo variables obligatorias. Act: instanciar `Settings()`. Assert: `settings.payments_mock is False`.

---

### 3.1 `GET /` — Health check (`backend/main.py`)

**Especificación**
- Entrada: ninguna.
- Salida: `{"status": "ok", "service": "tonal-tech-backend"}` con código 200.
- Regla de negocio: sirve como verificación de disponibilidad del servicio (usado por infraestructura/monitoreo).

**Casos de prueba (AAA)**
- `test_root_returns_ok_status`: Arrange: cliente de pruebas FastAPI (`TestClient`). Act: `GET /`. Assert: código 200 y body `{"status": "ok", "service": "tonal-tech-backend"}`.

---

### 3.2 Autenticación (`backend/routers/auth.py`)

#### 3.2.1 `POST /auth/register`

**Especificación**
- Entrada (`UserRegisterRequest`): `email` (formato válido), `password` (mínimo 8 caracteres).
- Salida (`TokenResponse`): `access_token`, `token_type="bearer"`, `user` (id, email, created_at).
- Reglas de negocio:
  - Si el email ya existe, responde `400 Bad Request` con detalle "El email ya está registrado".
  - La contraseña se almacena con hash `bcrypt` (nunca en texto plano).
  - Se genera un JWT firmado con `JWT_SECRET_KEY`/`JWT_ALGORITHM`, con expiración `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Casos borde: email con formato inválido (validación Pydantic devuelve 422); contraseña de 7 caracteres (422 por `min_length=8`).

**Casos de prueba (AAA)**
- `test_register_creates_user_and_returns_token`: Arrange: payload con email nuevo y password válido. Act: `POST /auth/register`. Assert: 200, `access_token` no vacío, `user.email` coincide.
- `test_register_rejects_duplicate_email`: Arrange: usuario ya registrado con `mismo@correo.com`. Act: `POST /auth/register` con el mismo email. Assert: 400 y detalle "El email ya está registrado".
- `test_register_rejects_short_password`: Arrange: payload con password de 5 caracteres. Act: `POST /auth/register`. Assert: 422 (validación Pydantic).
- `test_register_rejects_invalid_email_format`: Arrange: payload `email="no-es-email"`. Act: `POST /auth/register`. Assert: 422.
- `test_register_hashes_password`: Arrange: registrar usuario con password `"secreto123"`. Act: consultar el registro en la base. Assert: el campo `hashed_password` es distinto del texto plano y `verify_password` retorna `True` solo con la contraseña original.

#### 3.2.2 `POST /auth/login`

**Especificación**
- Entrada (`UserLoginRequest`): `email`, `password`.
- Salida: igual a `TokenResponse`.
- Reglas: si el usuario no existe o la contraseña no coincide, responde `401 Unauthorized` con detalle "Email o contraseña incorrectos" (mensaje genérico, no revela cuál dato falló).

**Casos de prueba (AAA)**
- `test_login_succeeds_with_valid_credentials`: Arrange: usuario previamente registrado. Act: `POST /auth/login` con credenciales correctas. Assert: 200 y `access_token` válido.
- `test_login_fails_with_wrong_password`: Arrange: usuario existente. Act: login con password incorrecta. Assert: 401, detalle "Email o contraseña incorrectos".
- `test_login_fails_with_unknown_email`: Arrange: email inexistente. Act: `POST /auth/login`. Assert: 401 (mismo mensaje genérico, no distingue de password incorrecta).

#### 3.2.3 `GET /auth/me`

**Especificación**
- Requiere header `Authorization: Bearer <token>`.
- Salida (`UserResponse`): datos del usuario autenticado.
- Reglas: token inválido/expirado → 401 "Token inválido o expirado"; token válido pero usuario borrado → 401 "Usuario no encontrado".

**Casos de prueba (AAA)**
- `test_get_me_returns_current_user`: Arrange: token válido de usuario registrado. Act: `GET /auth/me` con el token. Assert: 200 y payload con el email correcto.
- `test_get_me_rejects_missing_token`: Arrange: sin header Authorization. Act: `GET /auth/me`. Assert: 401 (falta de credenciales, según `HTTPBearer`).
- `test_get_me_rejects_invalid_token`: Arrange: token con firma corrupta. Act: `GET /auth/me`. Assert: 401 "Token inválido o expirado".
- `test_get_me_rejects_expired_token`: Arrange: token generado con `exp` en el pasado. Act: `GET /auth/me`. Assert: 401.

#### 3.2.4 `GET /auth/users/me/courses`

**Especificación**
- Requiere autenticación.
- Salida (`MyCoursesResponse`): lista de `MyCourseEntry` (course_id, name, image_path, total_lessons, completed_lessons, progress_pct).
- Regla de negocio: `progress_pct = round(completed * 100 / total)`; si `total == 0`, `progress_pct = 0` (evita división por cero).
- Solo incluye cursos donde el usuario tiene un `enrollment`.

**Casos de prueba (AAA)**
- `test_my_courses_returns_only_enrolled_courses`: Arrange: usuario con 1 enrollment de 3 cursos existentes. Act: `GET /auth/users/me/courses`. Assert: la respuesta contiene solo ese curso.
- `test_my_courses_computes_progress_percentage`: Arrange: curso con 4 lecciones, 2 completadas. Act: `GET /auth/users/me/courses`. Assert: `progress_pct == 50`.
- `test_my_courses_returns_empty_list_when_no_enrollments`: Arrange: usuario sin enrollments. Act: `GET /auth/users/me/courses`. Assert: `courses == []`.
- `test_my_courses_handles_zero_lesson_course_without_division_error`: Arrange: curso enrollado sin lecciones (`total=0`). Act: endpoint. Assert: `progress_pct == 0`, sin excepción.

---

### 3.3 Catálogo y progreso de cursos (`backend/routers/courses.py`)

#### 3.3.1 `GET /courses`

**Especificación**
- Autenticación **opcional** (`_optional_user_id`: si el token es inválido o ausente, continúa como anónimo en vez de fallar).
- Salida (`CourseListResponse`): lista de `CourseSummary` de cursos activos (`is_active=True`).
- Para usuario autenticado: incluye `enrolled` y `completed_lessons`; para anónimo: `enrolled=False`, `completed_lessons=0`.

**Casos de prueba (AAA)**
- `test_list_courses_anonymous_returns_all_active_courses_not_enrolled`: Arrange: 3 cursos activos, 1 inactivo, sin token. Act: `GET /courses`. Assert: 3 cursos, todos con `enrolled=False`.
- `test_list_courses_excludes_inactive_courses`: Arrange: curso con `is_active=False`. Act: `GET /courses`. Assert: no aparece en la lista.
- `test_list_courses_authenticated_marks_enrollment`: Arrange: usuario con enrollment en un curso. Act: `GET /courses` con token válido. Assert: ese curso tiene `enrolled=True` y `completed_lessons` correcto.
- `test_list_courses_with_invalid_token_behaves_as_anonymous`: Arrange: token corrupto en el header. Act: `GET /courses`. Assert: 200 (no 401), cursos con `enrolled=False`.

#### 3.3.2 `GET /courses/{course_id}`

**Especificación**
- Autenticación opcional.
- Salida (`CourseDetailResponse`): resumen del curso + `modules` con sus `lessons`.
- Regla de acceso por lección: `has_access = lesson.is_free OR (usuario autenticado AND tiene enrollment)`. `stream_available = has_access AND lesson.video_key no vacío`.
- Si el curso no existe o está inactivo → `404 Not Found` "Curso no encontrado".

**Casos de prueba (AAA)**
- `test_course_detail_returns_404_for_unknown_course`: Arrange: `course_id` inexistente. Act: `GET /courses/xxx`. Assert: 404.
- `test_course_detail_returns_404_for_inactive_course`: Arrange: curso con `is_active=False`. Act: `GET /courses/{id}`. Assert: 404.
- `test_course_detail_free_lesson_accessible_without_login`: Arrange: curso con una lección `is_free=True`, sin token. Act: `GET /courses/{id}`. Assert: esa lección tiene `has_access=True`.
- `test_course_detail_paid_lesson_blocked_without_enrollment`: Arrange: usuario autenticado sin enrollment, lección de pago. Act: `GET /courses/{id}` con token. Assert: `has_access=False`, `stream_available=False`.
- `test_course_detail_paid_lesson_unlocked_with_enrollment`: Arrange: usuario con enrollment en el curso. Act: `GET /courses/{id}`. Assert: todas las lecciones `has_access=True`; las que tienen `video_key` -> `stream_available=True`.
- `test_course_detail_lesson_without_video_key_has_stream_unavailable`: Arrange: lección con acceso pero `video_key=""`. Act: endpoint. Assert: `stream_available=False`.

#### 3.3.3 `GET /courses/{course_id}/progress`

**Especificación**
- Requiere autenticación.
- Regla: si el curso no existe → 404; si el usuario no tiene enrollment → `403 Forbidden` "No tienes acceso a este curso".
- Salida: lista de `LessonProgressEntry` del usuario para las lecciones del curso.

**Casos de prueba (AAA)**
- `test_course_progress_requires_enrollment`: Arrange: usuario autenticado sin enrollment. Act: `GET /courses/{id}/progress`. Assert: 403.
- `test_course_progress_returns_entries_for_enrolled_user`: Arrange: usuario con enrollment y progreso guardado en 2 lecciones. Act: endpoint. Assert: 200 con las 2 entradas.
- `test_course_progress_returns_404_for_unknown_course`: Arrange: `course_id` inexistente. Act: endpoint. Assert: 404.

#### 3.3.4 `PUT /lessons/{lesson_id}/progress`

**Especificación**
- Entrada (`LessonProgressUpdate`): `status` (`not_started|in_progress|completed`), `position_seconds >= 0`.
- Requiere autenticación y acceso a la lección (`user_has_lesson_access`: lección gratuita o enrollment en el curso).
- Efecto: crea o actualiza (`upsert`) el registro de progreso; si `status == completed`, setea `completed_at`; en otro caso lo limpia (`None`).
- Sin acceso → 403 "No tienes acceso a esta lección".

**Casos de prueba (AAA)**
- `test_update_progress_creates_new_record`: Arrange: usuario con acceso, sin progreso previo. Act: `PUT /lessons/{id}/progress` con `status=in_progress, position_seconds=120`. Assert: 200, se crea registro con esos valores.
- `test_update_progress_updates_existing_record`: Arrange: progreso previo `in_progress`. Act: `PUT` con `status=completed`. Assert: el registro se actualiza (no se duplica) y `completed_at` no es nulo.
- `test_update_progress_clears_completed_at_when_not_completed`: Arrange: lección marcada `completed`. Act: `PUT` con `status=in_progress`. Assert: `completed_at is None`.
- `test_update_progress_denies_access_without_enrollment`: Arrange: lección de pago, usuario sin enrollment. Act: `PUT /lessons/{id}/progress`. Assert: 403.
- `test_update_progress_rejects_negative_position`: Arrange: payload `position_seconds=-5`. Act: `PUT`. Assert: 422 (validación `ge=0`).

#### 3.3.5 `GET /lessons/{lesson_id}/stream-url`

**Especificación**
- Requiere autenticación y acceso a la lección.
- Regla: lección inexistente → 404; sin acceso → 403; lección sin `video_key` → 404 "Esta lección no tiene video disponible".
- Éxito: retorna `stream_url` generada por `get_presigned_download_url` (S3), válida por tiempo limitado (900s por defecto).

**Casos de prueba (AAA)**
- `test_stream_url_returns_404_for_unknown_lesson`: Arrange: `lesson_id` inexistente. Act: endpoint. Assert: 404.
- `test_stream_url_denies_access_without_enrollment`: Arrange: lección de pago, usuario sin enrollment. Act: endpoint. Assert: 403.
- `test_stream_url_returns_404_when_no_video_key`: Arrange: lección con acceso pero `video_key=""`. Act: endpoint. Assert: 404 "Esta lección no tiene video disponible".
- `test_stream_url_returns_presigned_url_on_success`: Arrange: lección con acceso y `video_key` válido; mock de `get_presigned_download_url`. Act: endpoint. Assert: 200 y `stream_url` igual al valor mockeado.

---

### 3.4 Pagos (`backend/routers/payments.py` + `backend/services/stripe.py`)

#### 3.4.1 `POST /payments/checkout-session`

**Especificación**
- Entrada (`CheckoutSessionRequest`): `course_id` (enum `CourseId`), `customer_email`.
- Salida (`CheckoutSessionResponse`): `session_id`, `checkout_url`.
- Reglas de negocio:
  - Si `PAYMENTS_MOCK=True`: crea una sesión simulada (`_create_mock_checkout_session`) que **completa el pago instantáneamente** (crea `purchase` con estado `complete` y otorga `enrollment` si el email corresponde a un usuario existente), sin llamar a Stripe.
  - Si `PAYMENTS_MOCK=False`: crea una `stripe.checkout.Session` real en modo `payment`, con `success_url` apuntando a `{APP_URL}/success?session_id={CHECKOUT_SESSION_ID}` y `cancel_url` a `{APP_URL}/cancel`; guarda un registro `Purchase` en estado `pending` con `video_key` mapeado por curso (`COURSE_VIDEO_KEYS`).
  - Si el `course_id` no tiene precio configurado en `PRICE_MAP` → `400 Bad Request`.

**Casos de prueba (AAA)**
- `test_checkout_session_mock_mode_completes_purchase_immediately`: Arrange: `settings.payments_mock=True`. Act: `POST /payments/checkout-session` con curso y email válidos. Assert: se retorna `session_id` con prefijo `cs_mock_`; el `Purchase` queda en estado `complete` inmediatamente.
- `test_checkout_session_real_mode_calls_stripe_and_creates_pending_purchase`: Arrange: `payments_mock=False`, mock de `stripe.checkout.Session.create`. Act: `POST /payments/checkout-session`. Assert: se llama a Stripe con `mode="payment"`, `metadata.course_id` correcto; se crea `Purchase` con `payment_status=pending`.
- `test_checkout_session_sets_correct_video_key_per_course`: Arrange: curso `scada-redes`. Act: crear sesión. Assert: `video_key == "videos/scada-redes"`.
- `test_checkout_session_rejects_course_without_price_mapping`: Arrange: `PRICE_MAP` sin entrada para un curso (escenario simulado). Act: `POST /payments/checkout-session`. Assert: 400 "Course pricing configuration not found".
- `test_checkout_session_rejects_invalid_email_format`: Arrange: `customer_email="no-valido"`. Act: endpoint. Assert: 422.

#### 3.4.2 `POST /payments/webhook`

**Especificación**
- Entrada: cuerpo crudo del webhook de Stripe + header `Stripe-Signature`.
- Regla: si falta el header → `400` "Stripe-Signature header is required".
- `construct_event` valida la firma con `STRIPE_WEBHOOK_SECRET`; si falla, `400` "Webhook signature verification failed".
- `handle_event`:
  - `checkout.session.completed` → marca `Purchase` como `complete` y ejecuta `grant_enrollment_from_purchase` (crea `enrollment` si existe un usuario con ese email, evitando duplicados).
  - `checkout.session.expired` → marca `Purchase` como `failed`.
  - Cualquier otro tipo de evento → responde `{"received": True, "type": event_type}` sin efectos secundarios (comportamiento "no-op" para eventos no manejados).

**Casos de prueba (AAA)**
- `test_webhook_rejects_missing_signature_header`: Arrange: request sin `Stripe-Signature`. Act: `POST /payments/webhook`. Assert: 400.
- `test_webhook_rejects_invalid_signature`: Arrange: firma inválida (mock de `stripe.Webhook.construct_event` lanzando `SignatureVerificationError`). Act: endpoint. Assert: 400 "Webhook signature verification failed".
- `test_webhook_checkout_completed_marks_purchase_complete`: Arrange: evento `checkout.session.completed` válido para una `Purchase` `pending` existente. Act: `handle_event(event)`. Assert: `Purchase.payment_status == complete`.
- `test_webhook_checkout_completed_grants_enrollment_when_user_exists`: Arrange: purchase completada con email de un usuario registrado. Act: `handle_event`. Assert: se crea un `Enrollment` para ese usuario y curso.
- `test_webhook_checkout_completed_does_not_grant_enrollment_when_user_missing`: Arrange: email de la compra no corresponde a ningún usuario. Act: `handle_event`. Assert: no se crea ningún `Enrollment`, sin excepción.
- `test_webhook_checkout_completed_avoids_duplicate_enrollment`: Arrange: enrollment ya existente para usuario/curso. Act: `handle_event` con el mismo evento otra vez (idempotencia). Assert: sigue existiendo un único `Enrollment`.
- `test_webhook_checkout_expired_marks_purchase_failed`: Arrange: evento `checkout.session.expired`. Act: `handle_event`. Assert: `Purchase.payment_status == failed`.
- `test_webhook_unhandled_event_type_returns_received_without_side_effects`: Arrange: evento de tipo `payment_intent.created`. Act: `handle_event`. Assert: retorna `{"received": True, "type": "payment_intent.created"}` y no modifica ninguna `Purchase`.

#### 3.4.3 `GET /payments/session-status/{session_id}`

**Especificación**
- Entrada: `session_id` en la ruta.
- Salida (`SessionStatusResponse`): `session_id`, `status`, `course_id`.
- Regla: si no existe la compra → `404 Not Found` "Sesión no encontrada".

**Casos de prueba (AAA)**
- `test_session_status_returns_purchase_info`: Arrange: `Purchase` existente con estado `complete`. Act: `GET /payments/session-status/{id}`. Assert: 200, `status == "complete"`, `course_id` correcto.
- `test_session_status_returns_404_for_unknown_session`: Arrange: `session_id` inexistente. Act: endpoint. Assert: 404.

---

### 3.5 Videos (`backend/routers/videos.py` + `backend/services/storage.py`)

#### 3.5.1 `POST /videos/upload-url`

**Especificación**
- Entrada (`UploadUrlRequest`): `object_key`, `content_type` (default `video/mp4`).
- Salida (`UploadUrlResponse`): `upload_url`, `object_key`.
- Regla: genera una URL PUT pre-firmada de S3 válida por `expires_in=900` segundos. No hay validación de autenticación en este endpoint (ver riesgo en sección 6).
- Si S3 falla (`BotoCoreError`/`ClientError`) → `RuntimeError` "Failed to create upload URL".

**Casos de prueba (AAA)**
- `test_upload_url_returns_presigned_put_url`: Arrange: mock de `s3_client.generate_presigned_url` retornando una URL fija. Act: `POST /videos/upload-url` con `object_key="videos/test.mp4"`. Assert: 200, `upload_url` igual al mock, `object_key` igual al enviado.
- `test_upload_url_uses_default_content_type_when_not_provided`: Arrange: payload sin `content_type`. Act: endpoint. Assert: se llama a S3 con `ContentType="video/mp4"`.
- `test_upload_url_raises_runtime_error_on_s3_failure`: Arrange: mock de S3 lanzando `ClientError`. Act: llamar `get_presigned_upload_url` directamente. Assert: se lanza `RuntimeError` con mensaje "Failed to create upload URL".

#### 3.5.2 `GET /videos/download-url`

**Especificación**
- Entrada (query params): `course_id`, `customer_email`.
- Regla: busca una `Purchase` con ese `course_id`+`customer_email` en estado `complete` (`get_completed_purchase`); si no existe → `403 Forbidden` "No completed purchase found for this course and customer."
- Éxito: retorna `download_url` presignada de S3 usando el `video_key` de la compra.
- Nota: este endpoint es el "legado" de descarga directa por email (independiente del flujo de streaming de lecciones vía `/lessons/{id}/stream-url`, que usa JWT).

**Casos de prueba (AAA)**
- `test_download_url_returns_403_without_completed_purchase`: Arrange: sin compras `complete` para ese email/curso. Act: `GET /videos/download-url?course_id=...&customer_email=...`. Assert: 403.
- `test_download_url_returns_presigned_url_for_completed_purchase`: Arrange: `Purchase` completa existente. Act: endpoint. Assert: 200 y `download_url` correspondiente al `video_key` de esa compra.
- `test_download_url_ignores_pending_purchases`: Arrange: `Purchase` en estado `pending` para el mismo email/curso. Act: endpoint. Assert: 403 (no se considera compra pendiente como válida).

---

### 3.6 Administración (`backend/routers/admin.py`)

**Especificación general**
- Todos los endpoints requieren JWT válido **y** que `user.is_admin == True` (verificado por `require_admin`); en caso contrario → `403 Forbidden` "Se requieren permisos de administrador".
- CRUD de **cursos**: crear (`id` debe cumplir patrón `^[a-z0-9-]+$`, min 2 caracteres), actualizar parcial (`PATCH`, solo campos enviados), eliminar (bloqueado con `409 Conflict` si el curso tiene enrollments — hay que desactivarlo en su lugar).
- CRUD de **módulos** y **lecciones**: crear/actualizar/eliminar; el borrado de un módulo o lección elimina en cascada el progreso asociado.
- **Enrollments manuales**: listar todas, otorgar (`grant_enrollment_by_email`, falla si usuario o curso no existen) y revocar (`revoke_enrollment_by_email`, 404 si no existe la inscripción).

**Casos de prueba (AAA)**
- `test_admin_endpoint_rejects_non_admin_user`: Arrange: usuario autenticado con `is_admin=False`. Act: `POST /admin/courses`. Assert: 403.
- `test_admin_endpoint_rejects_unauthenticated_request`: Arrange: sin token. Act: `POST /admin/courses`. Assert: 401.
- `test_create_course_succeeds_with_valid_id_pattern`: Arrange: admin autenticado, `id="curso-nuevo"`. Act: `POST /admin/courses`. Assert: 201, curso creado.
- `test_create_course_rejects_invalid_id_pattern`: Arrange: `id="Curso Invalido!"`. Act: endpoint. Assert: 422 (no cumple regex).
- `test_create_course_rejects_duplicate_id`: Arrange: curso ya existente con ese `id`. Act: `POST /admin/courses`. Assert: 400 "Ya existe un curso con id...".
- `test_update_course_applies_only_provided_fields`: Arrange: curso existente; payload con solo `name`. Act: `PATCH /admin/courses/{id}`. Assert: solo `name` cambia, el resto permanece igual.
- `test_update_course_returns_404_for_unknown_course`: Arrange: `course_id` inexistente. Act: `PATCH`. Assert: 404.
- `test_delete_course_blocks_when_enrollments_exist`: Arrange: curso con al menos un enrollment. Act: `DELETE /admin/courses/{id}`. Assert: 409 "No se puede eliminar: el curso tiene usuarios inscritos...".
- `test_delete_course_cascades_modules_and_lessons`: Arrange: curso sin enrollments, con módulos y lecciones. Act: `DELETE /admin/courses/{id}`. Assert: curso, módulos, lecciones y su progreso asociado se eliminan.
- `test_create_module_fails_for_unknown_course`: Arrange: `course_id` inexistente. Act: `POST /admin/courses/{id}/modules`. Assert: 404.
- `test_delete_module_cascades_lessons_and_progress`: Arrange: módulo con lecciones que tienen progreso. Act: `DELETE /admin/modules/{id}`. Assert: se eliminan lecciones y progreso relacionado.
- `test_create_lesson_fails_for_unknown_module`: Arrange: `module_id` inexistente. Act: `POST /admin/modules/{id}/lessons`. Assert: 404.
- `test_grant_enrollment_fails_for_unknown_user`: Arrange: email no registrado. Act: `POST /admin/enrollments`. Assert: 404 "Usuario '...' no encontrado".
- `test_grant_enrollment_is_idempotent`: Arrange: enrollment ya existente. Act: `POST /admin/enrollments` repetido. Assert: no se duplica el registro, respuesta 201 "granted: true".
- `test_revoke_enrollment_returns_404_when_not_found`: Arrange: no existe inscripción para ese email/curso. Act: `DELETE /admin/enrollments?email=...&course_id=...`. Assert: 404.
- `test_list_enrollments_returns_all_records_with_user_email`: Arrange: 2 enrollments de distintos usuarios. Act: `GET /admin/enrollments`. Assert: 200, lista con `user_email` correcto por join.

---

### 3.7 Servicio de persistencia (`backend/services/persistence.py`) — funciones clave

**Especificación**
- `init_db()`: crea tablas si no existen, agrega columna `is_admin` a `users` si falta (migración suave sin Alembic) y siembra (`seed_courses`) el catálogo `COURSE_SEED` (3 cursos) solo si no existen ya (idempotente).
- `hash_password` / `verify_password`: wrapper de `bcrypt`.
- `user_has_lesson_access(user_id, lesson_id)`: `True` si la lección es gratuita, o si el usuario tiene un `enrollment` en el curso al que pertenece el módulo de la lección; `False` si la lección no existe o el módulo no existe.
- `delete_course`: rechaza el borrado (`ValueError`) si existen enrollments asociados.

**Casos de prueba (AAA)**
- `test_init_db_is_idempotent_and_does_not_duplicate_seed_courses`: Arrange: base ya inicializada con los 3 cursos semilla. Act: llamar `init_db()` de nuevo. Assert: sigue habiendo exactamente 3 cursos (no se duplican).
- `test_init_db_adds_is_admin_column_to_existing_users_table`: Arrange: tabla `users` sin columna `is_admin` (simulando base preexistente). Act: `init_db()`. Assert: la columna existe después, con default `False`.
- `test_hash_password_and_verify_password_roundtrip`: Arrange: password `"MiClave123"`. Act: `hash_password` luego `verify_password` con la misma password. Assert: retorna `True`.
- `test_verify_password_fails_with_wrong_password`: Arrange: hash de `"correcta"`. Act: `verify_password("incorrecta", hash)`. Assert: `False`.
- `test_user_has_lesson_access_true_for_free_lesson_without_enrollment`: Arrange: lección `is_free=True`, usuario sin enrollment. Act: `user_has_lesson_access`. Assert: `True`.
- `test_user_has_lesson_access_false_for_paid_lesson_without_enrollment`: Arrange: lección de pago, usuario sin enrollment. Act: función. Assert: `False`.
- `test_user_has_lesson_access_false_for_unknown_lesson`: Arrange: `lesson_id` inexistente. Act: función. Assert: `False` (sin excepción).
- `test_delete_course_raises_value_error_with_enrollments`: Arrange: curso con enrollment. Act: `delete_course(course_id)`. Assert: lanza `ValueError`.

---

## 4. Frontend — Especificaciones (SDD) y casos de prueba (TDD Vanilla)

### 4.1 Páginas de Next.js (App Router)

#### 4.1.1 `app/page.tsx` — Landing pública (`/`)

**Especificación**
- Renderiza, envueltos en `LeadProvider`: `SiteHeader`, `TonalHero`, `ServiceGrid`, `AcademySection`, `ProofSection`, `SiteFooter`.
- No requiere autenticación; es contenido 100% estático (compatible con export estático).

**Casos de prueba (AAA)**
- `test_landing_page_renders_all_main_sections`: Arrange: renderizar `<Page/>`. Act: consultar el DOM. Assert: existen el header, hero, grid de servicios, sección academy, prueba social y footer.
- `test_landing_page_wraps_content_in_lead_provider`: Arrange: renderizar `<Page/>`. Act: disparar `useLead().openLead()` desde un componente hijo (ej. botón del hero). Assert: el panel lateral de diagnóstico se abre sin errores de contexto.

#### 4.1.2 `app/academy/page.tsx` — Plataforma Academy (`/academy`)

**Especificación**
- Renderiza `<AcademyPage/>` (client component) que gestiona el estado completo de autenticación, catálogo y visor de curso contra el backend real.

**Casos de prueba (AAA)**
- `test_academy_page_renders_academy_component`: Arrange: renderizar `<Page/>` de `/academy`. Act: consultar DOM. Assert: se monta `AcademyPage`.

#### 4.1.3 `app/success/page.tsx` — Confirmación de pago (`/success`)

**Especificación**
- Envuelve `<SuccessPage/>` en `<Suspense>` (requerido por Next.js al usar `useSearchParams`).
- Lee `session_id` de query string vía `SuccessPage`.

**Casos de prueba (AAA)**
- `test_success_page_wraps_component_in_suspense`: Arrange: renderizar la página sin que `useSearchParams` esté listo. Act: montar el árbol. Assert: no lanza error de "useSearchParams must be used inside Suspense".
- `test_success_page_shows_loading_state_before_session_resolves`: Arrange: mock de `getSessionStatus` pendiente. Act: renderizar con `?session_id=cs_123`. Assert: se muestra el spinner "Verificando tu pago...".

#### 4.1.4 `app/layout.tsx` — Layout raíz

**Especificación**
- Define fuentes (Geist Sans/Mono), metadata SEO, `lang="es"`, y monta `@vercel/analytics` **solo en producción** (`NODE_ENV === "production"`).

**Casos de prueba (AAA)**
- `test_layout_sets_spanish_lang_attribute`: Arrange: renderizar `RootLayout`. Act: inspeccionar el elemento `<html>`. Assert: `lang="es"`.
- `test_layout_does_not_render_analytics_in_development`: Arrange: `process.env.NODE_ENV = "development"`. Act: renderizar layout. Assert: el componente `Analytics` no se monta.
- `test_layout_renders_analytics_in_production`: Arrange: `process.env.NODE_ENV = "production"`. Act: renderizar layout. Assert: `Analytics` se monta.

---

### 4.2 `lib/api.ts` — Cliente HTTP del backend

**Especificación**
- `API_BASE_URL` = `NEXT_PUBLIC_API_BASE_URL` o `http://localhost:8000` por defecto.
- Gestión de token JWT en `localStorage` (`getToken`, `setToken`, `clearToken`), clave `academy_token`.
- `apiFetch<T>`: añade header `Authorization: Bearer <token>` si existe; si la respuesta es `401` y había token, lo limpia (`clearToken`) automáticamente (logout implícito por sesión expirada); si `!res.ok`, intenta extraer `detail` del JSON de error y lanza un `Error` con ese mensaje (o `Error ${status}` si no es JSON parseable).
- Expone funciones tipadas para cada endpoint del backend (auth, courses, progreso, pagos, streaming).
- `formatPrice(cents)`: formatea centavos a `"$XX.XX USD"`.

**Casos de prueba (AAA)**
- `test_get_token_returns_null_when_not_set`: Arrange: `localStorage` vacío. Act: `getToken()`. Assert: `null`.
- `test_set_and_get_token_roundtrip`: Arrange: `setToken("abc123")`. Act: `getToken()`. Assert: `"abc123"`.
- `test_clear_token_removes_stored_value`: Arrange: token previamente guardado. Act: `clearToken()` luego `getToken()`. Assert: `null`.
- `test_api_fetch_adds_authorization_header_when_token_present`: Arrange: token guardado, mock de `fetch`. Act: llamar cualquier función que use `apiFetch` (ej. `getMe`). Assert: `fetch` fue llamado con header `Authorization: Bearer <token>`.
- `test_api_fetch_clears_token_on_401_response`: Arrange: token guardado, mock de `fetch` retornando 401. Act: invocar `getMe()`. Assert: se lanza error y `getToken()` retorna `null` después.
- `test_api_fetch_throws_error_with_backend_detail_message`: Arrange: mock de `fetch` retornando 400 con body `{detail: "Curso no encontrado"}`. Act: invocar función. Assert: la promesa rechaza con `Error("Curso no encontrado")`.
- `test_api_fetch_throws_generic_error_when_body_not_json`: Arrange: mock de `fetch` retornando 500 sin body JSON válido. Act: invocar función. Assert: rechaza con `Error("Error 500")`.
- `test_format_price_formats_cents_correctly`: Arrange: `cents = 14900`. Act: `formatPrice(14900)`. Assert: `"$149.00 USD"`.
- `test_format_price_handles_zero`: Arrange: `cents = 0`. Act: `formatPrice(0)`. Assert: `"$0.00 USD"`.

---

### 4.3 `lib/products.ts` y `lib/tonal-data.ts` — Datos estáticos del frontend

**Especificación**
- `PRODUCTS`: arreglo fijo de 3 cursos (landing pública), fuente de verdad **solo del lado cliente** para mostrar contenido; el comentario del propio código indica la intención original de que "el servidor valide los precios contra este arreglo", pero **no existe actualmente ninguna validación server-side que lo use** (el backend tiene su propio catálogo independiente en `persistence.py`).
- `getProduct(id)`: retorna el curso o `undefined` si no existe.
- `formatPrice(cents)`: usa `Intl.NumberFormat("es-MX", {style:"currency", currency:"USD"})`.
- `tonal-data.ts`: catálogo estático de servicios B2B (`services`), categorías de filtro (`categoryFilters`), tamaños de empresa y categorías de formulario de leads.

**Casos de prueba (AAA)**
- `test_get_product_returns_product_for_known_id`: Arrange: `id="plc-industrial"`. Act: `getProduct(id)`. Assert: retorna el objeto con `name="Automatización con PLC"`.
- `test_get_product_returns_undefined_for_unknown_id`: Arrange: `id="no-existe"`. Act: `getProduct(id)`. Assert: `undefined`.
- `test_products_format_price_uses_es_mx_locale`: Arrange: `priceInCents=4900`. Act: `formatPrice(4900)`. Assert: cadena con formato de moneda USD estilo `es-MX` (p.ej. `"$49"` según `minimumFractionDigits:0`).
- `test_category_filters_includes_all_option_first`: Arrange: importar `categoryFilters`. Act: inspeccionar el arreglo. Assert: el primer elemento tiene `id: "all"`.
- `test_services_each_have_unique_id`: Arrange: importar `services`. Act: extraer todos los `id`. Assert: no hay duplicados.

---

### 4.4 Componentes de la landing pública

#### 4.4.1 `LeadProvider` / `useLead` (`components/lead-panel.tsx`)

**Especificación**
- Provee contexto React (`LeadContext`) con `openLead(presetService?)` para abrir un panel lateral ("Diagnóstico Técnico") de captura de leads en 3 pasos (Contacto → Perfil → Requerimiento).
- Validación por paso (`stepValid`):
  - Paso 0: `name.length > 1` y `email` cumple regex simple `^[^@\s]+@[^@\s]+\.[^@\s]+$`.
  - Paso 1: `size !== ""` y `service !== ""`.
  - Paso 2: `requirements.trim().length > 4`.
- `submit()`: simula un envío asíncrono con `setTimeout(2600ms)` pasando de `stage="diagnosing"` a `stage="done"`. **No hay llamada real a ningún backend/API** — es una simulación pura del lado cliente.
- Cierre con tecla `Escape` y bloqueo de scroll del `body` mientras el panel está abierto.
- `useLead()` lanza un error si se usa fuera de `LeadProvider`.

**Casos de prueba (AAA)**
- `test_use_lead_throws_outside_provider`: Arrange: renderizar un componente que llama `useLead()` sin `LeadProvider` como ancestro. Act: render. Assert: lanza `Error("useLead must be used within LeadProvider")`.
- `test_open_lead_resets_form_and_opens_panel`: Arrange: `LeadProvider` montado con datos previos en el formulario. Act: llamar `openLead("Servicio X")`. Assert: el panel es visible, el paso es 0, y `service` precargado es `"Servicio X"`.
- `test_step_zero_invalid_with_bad_email`: Arrange: paso 0, `email="correo-invalido"`. Act: evaluar `stepValid`. Assert: `false`, botón "Continuar" deshabilitado.
- `test_step_zero_valid_advances_to_step_one`: Arrange: `name="Ana"`, `email="ana@empresa.com"`. Act: clic en "Continuar". Assert: pasa a paso 1.
- `test_step_two_requires_min_length_requirements`: Arrange: paso 2, `requirements="hi"` (2 caracteres). Act: evaluar `stepValid`. Assert: `false`.
- `test_submit_moves_from_diagnosing_to_done_after_timeout`: Arrange: formulario completo y válido en paso 2. Act: clic en "Iniciar diagnóstico", avanzar el reloj simulado 2600ms. Assert: `stage` pasa de `"diagnosing"` a `"done"`.
- `test_escape_key_closes_panel`: Arrange: panel abierto. Act: disparar evento `keydown` con `key="Escape"`. Assert: el panel se cierra (`open=false`).
- `test_panel_locks_body_scroll_while_open`: Arrange: panel cerrado inicialmente. Act: `openLead()`. Assert: `document.body.style.overflow === "hidden"`; al cerrar, se restaura el valor original.

#### 4.4.2 `SiteHeader` (`components/site-header.tsx`)

**Especificación**
- Header fijo (`fixed`) que cambia de estilo (fondo con blur y borde) cuando `window.scrollY > 8`.
- Menú de navegación desktop con submenú "Soluciones B2B" (hover) y enlaces a `#servicios`, `/academy`, `#casos`.
- Menú mobile colapsable (`mobileOpen`), botón CTA "Diagnóstico Técnico Gratuito" que invoca `openLead()`.

**Casos de prueba (AAA)**
- `test_header_adds_scrolled_class_when_scrolled`: Arrange: montar `SiteHeader`, `window.scrollY = 0`. Act: simular scroll a `scrollY = 50` y disparar evento `scroll`. Assert: el header obtiene clases de fondo con blur.
- `test_mobile_menu_toggles_on_button_click`: Arrange: viewport mobile, menú cerrado. Act: clic en botón de menú (icono `Menu`). Assert: se muestra el panel de navegación mobile; un segundo clic lo oculta.
- `test_cta_button_calls_open_lead`: Arrange: `SiteHeader` dentro de `LeadProvider` con `openLead` espiado. Act: clic en "Diagnóstico Técnico Gratuito". Assert: `openLead` fue invocado sin argumentos.
- `test_academy_link_points_to_academy_route`: Arrange: renderizar header. Act: buscar el link "Academy". Assert: `href="/academy"`.

#### 4.4.3 `TonalHero` (`components/tonal-hero.tsx`)

**Especificación**
- Hero con CTA principal ("Agendar diagnóstico gratuito" → `openLead()`) y CTA secundario ("Explorar catálogo" → scroll suave a `#servicios`).

**Casos de prueba (AAA)**
- `test_primary_cta_opens_lead_panel`: Arrange: renderizar dentro de `LeadProvider`. Act: clic en botón primario. Assert: `openLead` se invoca.
- `test_secondary_cta_scrolls_to_services_section`: Arrange: existe un elemento `#servicios` en el DOM con `scrollIntoView` espiado. Act: clic en "Explorar catálogo". Assert: `scrollIntoView` fue llamado con `{behavior: "smooth"}`.

#### 4.4.4 `ServiceGrid` (`components/service-grid.tsx`)

**Especificación**
- Filtra `services` (de `tonal-data.ts`) por categoría (`categoryFilters`); `"all"` muestra todos.
- Cada tarjeta tiene botón "Cotizar servicio" que llama `openLead(service.title)`.

**Casos de prueba (AAA)**
- `test_default_filter_shows_all_services`: Arrange: render inicial. Act: contar tarjetas renderizadas. Assert: igual al total de `services`.
- `test_selecting_category_filters_services`: Arrange: render inicial. Act: clic en filtro `"support"`. Assert: solo se muestran tarjetas con `category === "support"`.
- `test_quote_button_opens_lead_with_service_title_preset`: Arrange: tarjeta de un servicio específico. Act: clic en "Cotizar servicio". Assert: `openLead` fue llamado con el `title` de ese servicio.

#### 4.4.5 `AcademySection` (`components/academy-section.tsx`)

**Especificación**
- Muestra grid de `PRODUCTS` (catálogo estático, no el del backend). Estado `unlocked: Set<string>` **en memoria de sesión** (no persiste tras recargar) que marca cursos "desbloqueados".
- Clic en una tarjeta abre `CourseDetail` en modal.

**Casos de prueba (AAA)**
- `test_academy_section_renders_all_static_products`: Arrange: render. Act: contar tarjetas. Assert: igual a `PRODUCTS.length`.
- `test_card_shows_lock_badge_when_not_unlocked`: Arrange: curso no desbloqueado. Act: inspeccionar tarjeta. Assert: se muestra el ícono `Lock` y el precio formateado.
- `test_card_shows_unlocked_badge_after_unlock`: Arrange: simular `handleUnlock(courseId)`. Act: re-render. Assert: la tarjeta muestra "Desbloqueado" con ícono `PlayCircle`.
- `test_clicking_card_opens_course_detail_modal`: Arrange: render inicial (`activeCourse=null`). Act: clic en una tarjeta. Assert: se monta `<CourseDetail/>` con el curso correspondiente.
- `test_unlock_state_does_not_persist_across_remount`: Arrange: curso desbloqueado en la instancia actual. Act: desmontar y remontar `AcademySection`. Assert: el curso vuelve a mostrarse bloqueado (estado en memoria, no persistido).

#### 4.4.6 `CourseDetail` (`components/course-detail.tsx`)

**Especificación**
- Modal con dos vistas: `overview` (contenido + panel de compra) y `checkout` (formulario ficticio que en realidad reabre el `LeadProvider` con `openLead("Academy / {nombre}")`).
- Botón "Desbloquear curso" (`!unlocked`) navega a `checkout`; el botón final "Solicitar acceso al curso" cierra el modal y abre el panel de leads — **no procesa ningún pago real**.
- Cierre con `Escape` y bloqueo de scroll del body, igual que `LeadProvider`.
- Lecciones con `preview: true` son accesibles aunque el curso no esté desbloqueado.

**Casos de prueba (AAA)**
- `test_free_preview_lessons_are_playable_when_locked`: Arrange: curso bloqueado con una lección `preview=true`. Act: inspeccionar esa lección. Assert: ícono `PlayCircle` (no `Lock`) y sin candado.
- `test_non_preview_lessons_locked_when_course_not_unlocked`: Arrange: curso bloqueado, lección sin `preview`. Act: inspeccionar. Assert: ícono `Lock`.
- `test_buy_button_switches_to_checkout_view`: Arrange: vista `overview`, curso bloqueado. Act: clic en "Desbloquear curso". Assert: se muestra la vista `checkout`.
- `test_checkout_request_access_closes_modal_and_opens_lead_panel`: Arrange: vista `checkout`. Act: clic en "Solicitar acceso al curso". Assert: `onClose` fue llamado y `openLead` fue invocado con `"Academy / {course.name}"`.
- `test_escape_key_closes_course_detail_modal`: Arrange: modal abierto. Act: `keydown Escape`. Assert: `onClose` invocado.

#### 4.4.7 `ProofSection` y `SiteFooter`

**Especificación**
- `ProofSection`: contenido 100% estático (métricas y casos de éxito hardcodeados), sin lógica de negocio dinámica.
- `SiteFooter`: CTA final que invoca `openLead()`; enlaces de columnas son anclas `href="#"` (no funcionales, placeholders).

**Casos de prueba (AAA)**
- `test_proof_section_renders_all_metrics`: Arrange: render. Act: contar bloques de métricas. Assert: 4 (según arreglo `metrics`).
- `test_footer_cta_opens_lead_panel`: Arrange: render dentro de `LeadProvider`. Act: clic en CTA final. Assert: `openLead` invocado.
- `test_footer_shows_current_year_in_copyright`: Arrange: mockear `Date` a un año fijo (ej. 2026). Act: render. Assert: el texto de copyright contiene "2026".

#### 4.4.8 `Button` (`components/ui/button.tsx`)

**Especificación**
- Wrapper de `@base-ui/react/button` con variantes (`default`, `outline`, `secondary`, `ghost`, `destructive`, `link`) y tamaños (`default`, `xs`, `sm`, `lg`, `icon`, etc.) vía `class-variance-authority`.
- Prop `disabled` deshabilita interacción y aplica opacidad reducida.

**Casos de prueba (AAA)**
- `test_button_applies_default_variant_classes`: Arrange: `<Button>Texto</Button>` sin props de variante. Act: inspeccionar `className`. Assert: contiene las clases de `variant: default`.
- `test_button_applies_outline_variant_classes`: Arrange: `<Button variant="outline">`. Act: inspeccionar clases. Assert: contiene clases de borde (`border-border`).
- `test_button_disabled_prevents_click_handler`: Arrange: `<Button disabled onClick={spy}>`. Act: clic simulado. Assert: `spy` no fue llamado.

---

### 4.5 Componentes de Academy (plataforma real conectada al backend)

#### 4.5.1 `AcademyPage` (`components/academy/academy-page.tsx`)

**Especificación**
- Orquesta 3 vistas: `catalog`, `course`, `login`.
- Al montar: siempre intenta `getCourses()` (catálogo público); si hay token guardado, intenta `getMe()` y, si tiene éxito, `getMyCourses()`; si `getMe()` falla (token inválido/expirado), el usuario queda como no autenticado (`user=null`) sin error visible bloqueante.
- `handleBuy(course)`: requiere `user` autenticado; llama `createCheckoutSession(course.id, user.email)` y redirige (`window.location.href`) a `checkout_url`; en error, muestra `checkoutError` y detiene el loading.
- `handleLogout()`: limpia token, resetea estado de usuario/cursos, vuelve a `catalog` y refresca catálogo.
- `openCourse(id)`: cambia a vista `course` y hace scroll al top.

**Casos de prueba (AAA)**
- `test_academy_page_loads_catalog_on_mount_even_without_token`: Arrange: sin token en `localStorage`, mock de `getCourses` con 3 cursos. Act: montar `AcademyPage`. Assert: se muestran las 3 tarjetas de catálogo, vista `login` no forzada.
- `test_academy_page_restores_session_when_token_valid`: Arrange: token válido guardado, mock de `getMe` exitoso. Act: montar componente. Assert: el header muestra el email del usuario y se cargan "Mis cursos".
- `test_academy_page_treats_invalid_token_as_logged_out`: Arrange: token guardado, mock de `getMe` rechazando (401). Act: montar componente. Assert: `user=null`, se muestra botón "Acceder" (no error visible).
- `test_handle_buy_redirects_to_checkout_url`: Arrange: usuario autenticado, mock de `createCheckoutSession` retornando `checkout_url="https://stripe.test/x"`. Act: invocar `handleBuy(course)`. Assert: `window.location.href` se establece a esa URL.
- `test_handle_buy_shows_error_on_failure`: Arrange: mock de `createCheckoutSession` rechazando con `Error("fallo pago")`. Act: `handleBuy(course)`. Assert: se muestra el mensaje "fallo pago" y `checkoutLoading=false`.
- `test_handle_logout_clears_session_and_returns_to_catalog`: Arrange: usuario autenticado en vista `course`. Act: `handleLogout()`. Assert: `user=null`, `myCourses=[]`, `view="catalog"`, token eliminado de `localStorage`.
- `test_open_course_switches_to_course_view_and_scrolls_top`: Arrange: vista `catalog`. Act: `openCourse("plc-industrial")`. Assert: `view="course"`, `activeCourseId="plc-industrial"`, `window.scrollTo` invocado con `{top:0}`.
- `test_catalog_card_shows_owned_badge_for_enrolled_course`: Arrange: `myCourses` incluye `course_id` de una tarjeta del catálogo. Act: render. Assert: esa tarjeta muestra "En tu biblioteca" en vez del precio.

#### 4.5.2 `LoginForm` (`components/academy/login-form.tsx`)

**Especificación**
- Pestañas `login`/`register`. En submit, llama `loginUser` o `registerUser` según la pestaña activa.
- Al éxito: `setToken(response.access_token)` y `onSuccess(response.user)`.
- Al error: muestra el mensaje (`err.message`) en un banner; en caso de error no-`Error`, muestra "Error desconocido".
- Input de contraseña exige `minLength=8` solo en modo `register` (validación HTML nativa).

**Casos de prueba (AAA)**
- `test_login_tab_calls_login_user_on_submit`: Arrange: tab `"login"`, campos llenos, mock de `loginUser` exitoso. Act: submit del formulario. Assert: `loginUser` invocado con email/password; `registerUser` no invocado.
- `test_register_tab_calls_register_user_on_submit`: Arrange: tab `"register"`. Act: submit. Assert: `registerUser` invocado, no `loginUser`.
- `test_successful_login_stores_token_and_calls_on_success`: Arrange: mock de `loginUser` resolviendo `{access_token:"tok", user:{...}}`. Act: submit. Assert: `setToken("tok")` invocado y `onSuccess(user)` invocado con el usuario recibido.
- `test_failed_login_shows_error_message`: Arrange: mock de `loginUser` rechazando con `Error("Email o contraseña incorrectos")`. Act: submit. Assert: se muestra ese texto en el banner de error.
- `test_switching_tabs_clears_previous_error`: Arrange: error visible tras un intento fallido en `login`. Act: clic en tab `register`. Assert: el banner de error desaparece.
- `test_loading_state_disables_submit_button_during_request`: Arrange: mock de `loginUser` con promesa pendiente. Act: submit. Assert: botón queda `disabled` y muestra spinner hasta que la promesa resuelve.

#### 4.5.3 `CourseViewer` (`components/academy/course-viewer.tsx`)

**Especificación**
- Carga el detalle del curso (`getCourseDetail`) al montar/cambiar `courseId`; si falla, muestra mensaje de error con botón "Volver al catálogo".
- Si el usuario está autenticado y `course.enrolled`, carga el progreso (`getCourseProgress`) y lo indexa en un `Map<lessonId, entry>`.
- `handleLessonClick(lesson)`:
  - Si `!lesson.has_access`: si no está autenticado, llama `onRequireLogin()`; si está autenticado pero sin acceso, no hace nada (lección bloqueada por no tener el curso).
  - Si `has_access` pero `!stream_available` (sin video cargado aún): no hace nada.
  - Si tiene acceso y stream disponible: fija `activeLesson`, montando el `VideoPlayer`.
- Muestra panel de compra ("Comprar curso" / "Inicia sesión para comprar") solo si `!course.enrolled`.
- Calcula `completedCount` y porcentaje de progreso general del curso.

**Casos de prueba (AAA)**
- `test_course_viewer_shows_error_state_on_load_failure`: Arrange: mock de `getCourseDetail` rechazando. Act: montar `CourseViewer`. Assert: se muestra el mensaje de error y botón "Volver al catálogo" que invoca `onBack`.
- `test_course_viewer_loads_progress_only_when_enrolled`: Arrange: `course.enrolled=false`. Act: montar componente. Assert: `getCourseProgress` no es invocado.
- `test_course_viewer_loads_progress_when_enrolled_and_authed`: Arrange: `course.enrolled=true`, `isAuthed=true`. Act: montar. Assert: `getCourseProgress` invocado y el mapa de progreso se puebla.
- `test_lesson_click_without_access_and_unauthenticated_requires_login`: Arrange: lección `has_access=false`, `isAuthed=false`. Act: clic en la lección. Assert: `onRequireLogin` invocado.
- `test_lesson_click_without_access_but_authenticated_does_nothing`: Arrange: lección `has_access=false`, `isAuthed=true` (usuario logueado sin el curso). Act: clic. Assert: no se activa ningún video, `onRequireLogin` no invocado.
- `test_lesson_click_with_access_sets_active_lesson`: Arrange: lección `has_access=true`, `stream_available=true`. Act: clic. Assert: se renderiza `VideoPlayer` con esa lección.
- `test_lesson_click_without_stream_available_does_nothing`: Arrange: lección con acceso pero `stream_available=false` (sin video cargado). Act: clic. Assert: no se activa el reproductor.
- `test_purchase_panel_hidden_when_course_already_enrolled`: Arrange: `course.enrolled=true`. Act: render. Assert: no se muestra el bloque de precio/compra.
- `test_purchase_panel_buy_button_requires_login_when_unauthenticated`: Arrange: `course.enrolled=false`, `isAuthed=false`. Act: clic en botón de compra. Assert: `onRequireLogin` invocado (no `onBuy`).
- `test_progress_percentage_computed_correctly`: Arrange: 5 lecciones totales, progreso con 2 `completed`. Act: render. Assert: barra de progreso muestra `40%`.

#### 4.5.4 `VideoPlayer` (`components/academy/video-player.tsx`)

**Especificación**
- Al montar/cambiar `lessonId`, obtiene `getStreamUrl(lessonId)` y la asigna como `src` del `<video>`.
- Si `startAt > 0` y `startAt < duration - 5`, reanuda la reproducción en ese punto (`onLoadedMetadata`), solo una vez por carga (`resumedRef`).
- Reporta progreso (`saveLessonProgress`) cada `PROGRESS_INTERVAL_MS=10000` mientras el video se reproduce (`!paused && !ended`), en pausa (`in_progress`), y al finalizar (`completed`, además invoca `onCompleted`).
- Estados: cargando (spinner), error (mensaje), reproductor listo.
- Los errores de red al guardar progreso se ignoran silenciosamente (`.catch(() => {})`) — no bloquean la reproducción.

**Casos de prueba (AAA)**
- `test_video_player_shows_loading_state_before_url_resolves`: Arrange: mock de `getStreamUrl` con promesa pendiente. Act: montar componente. Assert: se muestra el spinner.
- `test_video_player_shows_error_state_on_stream_url_failure`: Arrange: mock de `getStreamUrl` rechazando con `Error("No se pudo cargar el video")`. Act: montar. Assert: se muestra el mensaje de error.
- `test_video_player_resumes_at_start_at_when_valid`: Arrange: `startAt=120`, `duration=600` (mock del elemento video). Act: disparar evento `loadedmetadata`. Assert: `video.currentTime` se fija en `120`.
- `test_video_player_does_not_resume_when_start_at_near_end`: Arrange: `startAt=598`, `duration=600` (menos de 5s de margen). Act: `loadedmetadata`. Assert: `currentTime` no se modifica.
- `test_video_player_reports_in_progress_on_interval_while_playing`: Arrange: video en reproducción (`paused=false`). Act: avanzar el temporizador simulado 10000ms. Assert: `saveLessonProgress` invocado con `status="in_progress"`.
- `test_video_player_does_not_report_progress_while_paused`: Arrange: `video.paused=true`. Act: avanzar 10000ms. Assert: `saveLessonProgress` no invocado por el intervalo.
- `test_video_player_reports_completed_and_calls_on_completed_on_ended`: Arrange: video reproduciéndose. Act: disparar evento `ended`. Assert: `saveLessonProgress` invocado con `status="completed"` y `onCompleted` invocado.
- `test_video_player_report_failure_does_not_throw`: Arrange: mock de `saveLessonProgress` rechazando. Act: disparar evento `ended`. Assert: no se propaga ninguna excepción no controlada.

#### 4.5.5 `SuccessPage` (`components/academy/success-page.tsx`)

**Especificación**
- Lee `session_id` de la query string; si falta, muestra error "Falta el identificador de la sesión de pago." sin llamar al backend.
- Si existe, llama `getSessionStatus(sessionId)`; en error de red, muestra mensaje genérico ("No pudimos verificar tu pago...").
- Si `session.status === "complete"`, muestra "Pago completado" y enlace "Ir a mis cursos"; en cualquier otro estado, "Pago en proceso" y enlace "Volver a Academy".

**Casos de prueba (AAA)**
- `test_success_page_shows_error_when_session_id_missing`: Arrange: `useSearchParams` sin `session_id`. Act: montar `SuccessPage`. Assert: se muestra "Falta el identificador de la sesión de pago."; `getSessionStatus` no se invoca.
- `test_success_page_shows_completed_message_for_complete_status`: Arrange: `session_id` presente, mock de `getSessionStatus` resolviendo `{status:"complete", course_id:"plc-industrial"}`. Act: montar. Assert: se muestra "Pago completado" y enlace "Ir a mis cursos".
- `test_success_page_shows_pending_message_for_other_status`: Arrange: mock resolviendo `{status:"pending"}`. Act: montar. Assert: se muestra "Pago en proceso".
- `test_success_page_shows_generic_error_on_network_failure`: Arrange: mock de `getSessionStatus` rechazando. Act: montar. Assert: se muestra el mensaje "No pudimos verificar tu pago...".

---

## 5. Infraestructura / Despliegue

### 5.1 Contenedores

**Especificación**
- `Dockerfile.frontend`: imagen `node:20-alpine`; habilita `pnpm@9.15.9` vía `corepack`; instala dependencias con `--frozen-lockfile`; recibe `NEXT_PUBLIC_API_BASE_URL` como build-arg/env; expone el puerto `3000`; comando por defecto `pnpm dev --hostname 0.0.0.0` (es decir, el contenedor corre en **modo desarrollo**, no `next start` sobre un build de producción).
- `backend/Dockerfile`: imagen `python:3.12-slim`; instala dependencias de `requirements.txt`; copia el código de `backend/`; **copia `backend/` completo como `.env`** (`COPY backend/ .env`, línea que parece un posible error/atajo, ver riesgos); expone `8000`; ejecuta `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload` (también en modo `--reload`, no apto para producción tal cual).
- `podman-compose.yml`: define servicios `frontend` (build desde `Dockerfile.frontend`, puerto `3000:3000`, depende de `backend`) y `backend` (build desde `backend/Dockerfile`, variables desde `backend/.env`, puerto `8000:8000`).

**Casos de prueba (AAA)** — validación de infraestructura como pruebas de "smoke"/integración
- `test_frontend_image_builds_successfully`: Arrange: contexto del repo. Act: `podman build -f Dockerfile.frontend .`. Assert: build finaliza con código 0.
- `test_backend_image_builds_successfully`: Arrange: contexto del repo. Act: `podman build -f backend/Dockerfile .`. Assert: build finaliza con código 0.
- `test_compose_up_exposes_expected_ports`: Arrange: `podman-compose up -d`. Act: consultar contenedores en ejecución. Assert: puertos `3000` y `8000` mapeados y accesibles (`GET http://localhost:8000/` responde 200; `GET http://localhost:3000/` responde 200).
- `test_backend_container_starts_only_after_env_file_present`: Arrange: eliminar temporalmente `backend/.env`. Act: `podman-compose up backend`. Assert: el contenedor falla al iniciar (por variables obligatorias faltantes en `Settings`), evidenciando la dependencia dura del archivo de entorno.

### 5.2 CI/CD (`.github/workflows/deploy.yml`)

**Especificación**
- Trigger: `push` a la rama `main`.
- Pasos: checkout → `setup-node@v4` (Node 22) → instala `pnpm` global → `pnpm install --no-frozen-lockfile` → `pnpm run build` (equivalente a `next build` con `output:"export"`, genera `./out`) → sube artefacto con `upload-pages-artifact` → despliega con `deploy-pages`.
- Permisos: `contents: read`, `pages: write`, `id-token: write` (requeridos para el flujo OIDC de GitHub Pages).
- **No incluye ningún paso para el backend** (no hay build/push de imagen del backend, ni pruebas automatizadas de frontend o backend en el pipeline).

**Casos de prueba (AAA)**
- `test_workflow_triggers_only_on_main_branch_push`: Arrange: leer `deploy.yml`. Act: inspeccionar `on.push.branches`. Assert: contiene únicamente `["main"]`.
- `test_workflow_build_step_runs_pnpm_build`: Arrange: leer el workflow. Act: inspeccionar el step "Build static site". Assert: comando `pnpm run build`.
- `test_workflow_uploads_out_directory_as_artifact`: Arrange: inspeccionar step `upload-pages-artifact`. Act: leer `with.path`. Assert: `./out`.
- `test_workflow_has_no_backend_test_or_deploy_step` (prueba de "ausencia", documentando deuda): Arrange: inspeccionar todos los `jobs`/`steps` del workflow. Act: buscar referencias a `backend`, `pytest`, `docker build backend`. Assert: no existe ninguna — el backend no se prueba ni despliega en este pipeline.

### 5.3 Variables de entorno necesarias

**Frontend** (`.env.local`, ver `.env.local.example`):
- `NEXT_PUBLIC_API_BASE_URL` — URL base del backend consumida por `lib/api.ts`.
- `NEXT_PUBLIC_BASE_PATH` — inyectada automáticamente por `next.config.mjs` (`/tonal-tech-landing`) para el export estático en GitHub Pages; no se define manualmente en `.env`.

**Backend** (`backend/.env`, ver `backend/.env.example` y `backend/config.py`):
- `STRIPE_SECRET_KEY` — clave secreta de Stripe (obligatoria).
- `STRIPE_WEBHOOK_SECRET` — secreto para verificar firmas de webhooks (obligatoria).
- `STRIPE_PRICE_ID` — ID de precio de Stripe usado para los 3 cursos (obligatoria; actualmente el mismo precio se reutiliza para los tres cursos vía `PRICE_MAP`).
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — credenciales de AWS para S3 (obligatorias).
- `AWS_REGION` — región de S3 (default `us-east-1`).
- `AWS_S3_BUCKET` — bucket de S3 con los videos (obligatoria).
- `CORS_ORIGINS` — orígenes permitidos, separados por coma (default `http://localhost:3000`).
- `DATABASE_URL` — cadena de conexión PostgreSQL (o SQLite en desarrollo).
- `APP_URL` — URL pública del frontend, usada para construir `success_url`/`cancel_url` de Stripe.
- `PAYMENTS_MOCK` — si es `true`, simula pagos sin llamar a Stripe (útil para desarrollo/demo).
- `JWT_SECRET_KEY` — secreto de firma de tokens JWT (tiene un valor por defecto inseguro que **debe cambiarse en producción**, ver riesgos).
- `JWT_ALGORITHM` — algoritmo de firma JWT (default `HS256`).
- `ACCESS_TOKEN_EXPIRE_MINUTES` — expiración del token (default 1440 = 24h).

---

## 6. Riesgos, deuda técnica y áreas sin cobertura de pruebas

1. **Ausencia total de pruebas automatizadas en el repositorio.** No existe carpeta `tests/` ni configuración de `pytest`, `jest`, `vitest` o similar en `package.json`/`pyproject.toml`. Todos los casos de prueba descritos en este documento son una propuesta derivada de las especificaciones (SDD+TDD), no pruebas ya implementadas.
2. **Dos catálogos de cursos desincronizados**: `lib/products.ts` (frontend, landing pública) vs. el catálogo real en `backend/services/persistence.py` (`COURSE_SEED`). Tienen IDs, precios y cantidad de lecciones distintos (`scada-networks` vs `scada-redes`, `robotics` vs `robotica-industrial`; precios `4900/7900/9900` vs `14900/18900/12900`). El flujo de "Academy" de la landing pública (`AcademySection`/`CourseDetail`) **no compra nada real**: solo simula desbloqueo en memoria y reabre el panel de leads. Riesgo de confusión para el usuario y de mantenimiento duplicado.
3. **Endpoint `POST /videos/upload-url` sin autenticación ni autorización.** Cualquier cliente que conozca la URL del backend puede solicitar una URL de subida pre-firmada a S3 para cualquier `object_key`, sin verificar que sea un administrador o un flujo autorizado. Riesgo de sobrescritura/subida arbitraria de objetos en el bucket.
4. **`GET /videos/download-url` no usa JWT**, se basa únicamente en `course_id` + `customer_email` de query string para validar una compra completada. Un atacante que conozca (o adivine) el email de un comprador legítimo y el `course_id` podría obtener una URL de descarga del video sin autenticarse. El flujo más nuevo (`/lessons/{id}/stream-url`) sí exige JWT y control de acceso por enrollment — sería recomendable unificar/deprecar el endpoint legado.
5. **`JWT_SECRET_KEY` con valor por defecto hardcodeado** (`"change-me-in-production-please-32chars"`) en `backend/config.py`. Si no se sobreescribe explícitamente en el entorno de producción, todos los tokens serían falsificables por cualquiera que lea el código fuente público.
6. **`backend/Dockerfile` contiene `COPY backend/ .env`**, lo cual copia el directorio completo de `backend/` sobre un archivo llamado `.env` en el WORKDIR — esto no coincide con la intención habitual de copiar un archivo `.env` real y es probable que sea un error de la Dockerfile (no crea variables de entorno utilizables; el compose depende de `env_file: backend/.env` para inyectarlas en tiempo de ejecución, así que en la práctica funciona solo por ese mecanismo externo, no por la instrucción `COPY`).
7. **Contenedores en modo desarrollo dentro de docker-compose de referencia**: el frontend corre `pnpm dev` y el backend `uvicorn --reload`, ambos pensados para desarrollo, no para una imagen de producción optimizada (sin build de producción de Next.js, sin múltiples workers de Uvicorn, sin usuario no-root, etc.).
8. **Pipeline de CI/CD solo cubre el frontend estático.** No hay ningún job que instale dependencias de Python, ejecute pruebas de backend, valide tipado (`tsc --noEmit`) ni ejecute linting (`eslint`) antes de desplegar; tampoco hay build/publish de la imagen del backend.
9. **Falta de invalidación de "compras completadas" duplicadas o reembolsos**: `handle_event` no maneja eventos como `charge.refunded` o `checkout.session.async_payment_failed`; un reembolso no revoca automáticamente el `enrollment` otorgado.
10. **`typescript.ignoreBuildErrors: true`** en `next.config.mjs` permite que el build de producción continúe aunque existan errores de tipado, reduciendo la garantía que da TypeScript estricto declarado en el enunciado del proyecto.
11. **Regla de validación de email del panel de leads** (`lead-panel.tsx`) usa una regex simple del lado cliente sin validación de servidor (no hay backend real detrás del formulario de leads; es 100% simulado con `setTimeout`).
12. **Falta de tests de concurrencia/idempotencia en `grant_enrollment_from_purchase` y `grant_enrollment_by_email`** ante llamadas simultáneas (aunque el `UniqueConstraint` de la tabla `enrollments` mitigaría duplicados a nivel de base de datos, no hay pruebas que verifiquen el manejo de la excepción de integridad resultante).
13. **`PRICE_MAP` usa el mismo `STRIPE_PRICE_ID` para los tres cursos**, a pesar de que `COURSE_SEED` define `price_cents` distintos por curso — es decir, el precio real cobrado por Stripe depende únicamente de la configuración del Price en el dashboard de Stripe, no de `price_cents` del backend; ambos deben mantenerse sincronizados manualmente (riesgo de desalineación entre lo mostrado en la UI y lo efectivamente cobrado).
14. **No hay manejo de expiración/renovación de URLs pre-firmadas de streaming en el reproductor**: si una lección dura más de 900 segundos (15 minutos, el `expires_in` por defecto), la URL firmada podría expirar durante la reproducción sin un mecanismo de refresco visible en `VideoPlayer`.

---

*Documento generado a partir de una revisión exhaustiva y directa del código fuente del repositorio `tonal-tech-landing` (backend, frontend, configuración e infraestructura). No se leyeron ni se exponen valores de archivos `.env` reales; solo se referencian los nombres de las variables de entorno requeridas.*
