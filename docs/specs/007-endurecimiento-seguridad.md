# 007 - Endurecimiento de seguridad y calidad de la versión actual (deuda técnica)

- **Estado:** aprobada (2026-09-29)
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

Esta spec resuelve los **14 riesgos/deuda técnica** documentados en `ANALISIS-PROYECTO.md` (sección 6) y consolida la **Fase 1** del roadmap (spec 001): endurecer la base antes de construir las features nuevas (002–006). Sin esta fase, cualquier funcionalidad nueva se apoya en un backend con endpoints públicos inseguros, catálogos duplicados, contenedores de desarrollo y cero pruebas automatizadas.

Se organiza en 11 ítems (a)–(k), cada uno con su especificación funcional (SDD) y sus casos de prueba (TDD Vanilla):

- (a) Autenticación en `POST /videos/upload-url` (riesgo #3).
- (b) Deprecar/reemplazar `GET /videos/download-url` por flujo JWT (riesgo #4).
- (c) `JWT_SECRET_KEY` sin default inseguro (riesgo #5).
- (d) Unificar catálogos de cursos (riesgos #2 y #13).
- (e) Corregir `backend/Dockerfile` (riesgo #6).
- (f) Contenedores de producción (riesgo #7).
- (g) CI/CD con tests y build de backend (riesgos #1, #8 y #12).
- (h) Manejo de reembolsos en webhook (riesgo #9).
- (i) Quitar `typescript.ignoreBuildErrors` (riesgo #10).
- (j) Refresco de URLs pre-firmadas en `VideoPlayer` (riesgo #14).
- (k) Autenticación en `POST /payments/checkout-session` (deuda de 004).

El riesgo #11 (validación de email del lead) lo resuelve la spec 002.

## 2. Objetivos

- Eliminar los endpoints públicos sin autenticación que permiten subir/descargar objetos de S3 arbitrariamente.
- Eliminar el secreto JWT hardcodeado con valor por defecto.
- Unificar el catálogo de cursos en una sola fuente de verdad (backend).
- Corregir la infraestructura: Dockerfiles, contenedores de producción y CI/CD con pruebas.
- Manejar reembolsos y fallos de pago asíncronos en el webhook de Stripe.
- Restaurar la garantía de TypeScript en el build.
- Evitar cortes de reproducción por expiración de URLs pre-firmadas.
- Exigir JWT en `POST /payments/checkout-session` (deuda de 004).

## 3. Alcance

### Incluye
- Los 11 ítems (a)–(k) con su especificación y pruebas.
- Ajustes en `backend/routers/videos.py`, `backend/config.py`, `backend/services/persistence.py`, `backend/services/stripe.py`, `backend/routers/payments.py`.
- Ajustes en `Dockerfile.frontend`, `backend/Dockerfile`, `podman-compose.yml`, `.github/workflows/deploy.yml`, `next.config.mjs`.
- Ajustes en `lib/products.ts`/`components/academy-section.tsx`/`components/course-detail.tsx` (unificación de catálogo) y `components/academy/video-player.tsx` (refresco de URL).
- Creación de la suite de pruebas: `backend/tests/` (pytest) y scripts de frontend (`lint`, `typecheck` ya existen en `package.json`).

### Excluye
- Features nuevas de negocio (002–006).
- Migración de BD fuera de lo necesario para (d) y (h).
- Cambios de diseño visual del frontend.

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | (a) `POST /videos/upload-url` exige JWT + `is_admin` | Alta |
| R2 | (b) `GET /videos/download-url` exige JWT + verificación de compra/enrollment; se marca deprecado | Alta |
| R3 | (c) `JWT_SECRET_KEY` sin default; la app falla al arrancar si falta en producción | Alta |
| R4 | (d) Un solo catálogo de cursos: el backend es la fuente de verdad; `lib/products.ts` se elimina o se reemplaza por datos del backend | Alta |
| R5 | (d) `PRICE_MAP` se elimina o se sincroniza por curso (cada curso con su `STRIPE_PRICE_ID` o precio propio) | Alta |
| R6 | (e) `backend/Dockerfile` sin `COPY backend/ .env`; el entorno se inyecta vía `env_file`/variables | Alta |
| R7 | (f) Imagen de producción del frontend (build estático servido por nginx) y backend sin `--reload` | Alta |
| R8 | (g) CI/CD: job de tests backend (pytest), job de lint + `tsc --noEmit` frontend, build de imagen backend | Alta |
| R9 | (h) Webhook maneja `charge.refunded` (revoca enrollment) y `checkout.session.async_payment_failed` | Alta |
| R10 | (i) `typescript.ignoreBuildErrors: false` (o eliminar la opción) | Media |
| R11 | (j) `VideoPlayer` refresca la URL pre-firmada antes de expirar (o al fallar) | Media |
| R12 | (g) Pruebas de concurrencia/idempotencia en `grant_enrollment_from_purchase` y `grant_enrollment_by_email` | Media |
| R13 | (k) `POST /payments/checkout-session` exige JWT (`get_current_user_id`) | Alta |

> **Nota:** requirements.txt fija fastapi>=0.122 para garantizar 401 sin credenciales.

## 5. Diseño / Arquitectura

### 5.1 (a) Autenticación en `POST /videos/upload-url`

- **Estado actual:** `backend/routers/videos.py` define `upload_url(payload)` sin dependencia de autenticación; cualquier cliente puede pedir una URL pre-firmada de subida para cualquier `object_key`.
- **Cambio:** añadir `_: int = Depends(require_admin)` (reutilizando `require_admin` de `backend/routers/admin.py`). Solo admins pueden solicitar URLs de subida.
- **Impacto:** el flujo de subida de videos (hoy manual/administrativo) no cambia de forma; se documenta que la subida de lecciones es operación de admin.

### 5.2 (b) Deprecar `GET /videos/download-url`

- **Estado actual:** `download_url(course_id, customer_email)` valida compra solo con email+course_id en query, sin JWT.
- **Cambio:**
  1. El endpoint exige JWT (`get_current_user_id`).
  2. Verifica que el usuario tenga enrollment en el curso (misma lógica de acceso que `/lessons/{id}/stream-url`).
  3. Se elimina el parámetro `customer_email` de la query (el usuario se deriva del token).
  4. Se marca como deprecado (header `Deprecation: true` y docstring) porque el flujo moderno es `/lessons/{id}/stream-url`.
  5. Opcional: eliminar el endpoint en una iteración posterior si ningún cliente lo usa (verificar con grep antes de eliminar).
- **Impacto:** rompe cualquier cliente que use el endpoint viejo sin token; se documenta la migración.

### 5.3 (c) `JWT_SECRET_KEY` obligatoria

- **Estado actual:** `backend/config.py` define `JWT_SECRET_KEY` con default `"change-me-in-production-please-32chars"`.
- **Cambio:** quitar el default. La variable pasa a ser **obligatoria** (pydantic-settings falla al arrancar si falta). `backend/.env.example` documenta un valor de desarrollo de ejemplo (nunca el mismo en producción).
- **Impacto:** cualquier entorno sin la variable deja de arrancar (fail-fast), evitando tokens falsificables.

### 5.4 (d) Unificar catálogos de cursos

- **Estado actual:** `lib/products.ts` (frontend, IDs `plc-industrial`, `scada-networks`, `robotics`, precios `4900/7900/9900`) vs `COURSE_SEED` del backend (IDs `plc-industrial`, `scada-redes`, `robotica-industrial`, precios `14900/18900/12900`). `AcademySection`/`CourseDetail` de la landing usan el catálogo estático y su "compra" solo reabre el panel de leads.
- **Cambio:**
  1. **Fuente de verdad única:** el backend (`COURSE_SEED` + tabla `courses`).
  2. `AcademySection` y `CourseDetail` (landing) pasan a consumir `GET /courses` vía `lib/api.ts` (mismo patrón que `/academy`).
  3. El botón de compra de la landing enlaza a `/academy` (login + compra real) en lugar de abrir el panel de leads.
  4. `lib/products.ts` se elimina (verificar con grep que no quede ningún import).
  5. **`PRICE_MAP`:** se elimina el mapeo único; cada curso usa su `price_cents` y, si aplica, su propio `STRIPE_PRICE_ID` (nueva columna `stripe_price_id` nullable en `courses`, o configuración por curso). El precio cobrado por Stripe debe coincidir con `price_cents` (validación en checkout).
  6. **Enum `CourseId` (hallazgo de esta revisión, verificado en código):** `CheckoutSessionRequest.course_id` está tipado como el enum `CourseId` (`backend/schemas.py`) con solo 3 valores, y `Purchase.course_id` es `SqlEnum(CourseId)` en la tabla `purchases`; además `COURSE_VIDEO_KEYS` en `backend/services/stripe.py` mapea los 3 cursos a prefijos de video hardcodeados. Consecuencia: **ningún curso creado por el admin (005) puede venderse** — el checkout responde 422 antes de tocar la lógica, y en PostgreSQL el enum de la columna bloquearía inserts con otros valores. La unificación exige: (i) `CheckoutSessionRequest.course_id: str` validado contra la tabla `courses` (404/400 si no existe o inactivo); (ii) `Purchase.course_id` migrado a `String`; (iii) `COURSE_VIDEO_KEYS` eliminado (el `video_key` ya se deriva por lección en el seed y en el admin).
- **Impacto:** elimina la duplicación (riesgo #2) y la desalineación de precios (riesgo #13).

### 5.5 (e) Corregir `backend/Dockerfile`

- **Estado actual:** `COPY backend/ .env` copia el directorio `backend/` sobre un archivo llamado `.env` (no crea variables utilizables; el compose inyecta el entorno vía `env_file`).
- **Cambio:** eliminar la línea `COPY backend/ .env`. El entorno se inyecta exclusivamente vía `env_file: backend/.env` en `podman-compose.yml` (mecanismo que ya funciona) o variables de entorno del orquestador.
- **Impacto:** imagen más limpia; se elimina un archivo `.env` falso dentro de la imagen.

### 5.6 (f) Contenedores de producción

- **Estado actual:** `Dockerfile.frontend` corre `pnpm dev`; `backend/Dockerfile` corre `uvicorn --reload`.
- **Cambio:**
  - **Frontend:** como el proyecto usa `output: "export"`, **no existe `next start`** (requeriría quitar el export estático). La imagen de producción será multi-stage: stage de build (`pnpm build` genera `out/`) + stage runtime con **nginx** sirviendo `out/` (puerto 80). Se documenta esta decisión: si en el futuro se quiere `next start`, habrá que quitar `output: "export"` y migrar el deploy de GitHub Pages.
  - **Backend:** `CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]` (sin `--reload`), usuario no-root (`USER app`), y `HEALTHCHECK` opcional contra `GET /`.
  - **`podman-compose.yml`:** perfiles `dev` (comportamiento actual) y `prod` (imágenes de producción), o simplemente apuntar a las imágenes nuevas.
- **Impacto:** contenedores listos para producción; el flujo de desarrollo local sigue usando `pnpm dev`/`uvicorn --reload` fuera de las imágenes.

### 5.7 (g) CI/CD con pruebas

- **Estado actual:** `.github/workflows/deploy.yml` solo construye y despliega el frontend estático; sin tests, sin lint, sin backend.
- **Cambio:** nuevo workflow (o ampliación del existente) con jobs:
  1. **backend-tests:** `setup-python@v5` (3.12) → instalar `backend/requirements.txt` (+ `pytest`) → `pytest backend/tests` (con `DATABASE_URL` de SQLite de prueba y `PAYMENTS_MOCK=true`).
  2. **frontend-checks:** `setup-node@v4` + pnpm → `pnpm install --frozen-lockfile` → `pnpm run lint` → `pnpm run typecheck` (`tsc --noEmit`).
  3. **backend-image:** `docker/build-push-action` (o `podman build`) para construir la imagen del backend y publicarla en un registry (GHCR) — al menos build de verificación.
  4. **deploy:** job existente de GitHub Pages, que ahora **depende** de que 1–3 pasen.
- **Pruebas de concurrencia (riesgo #12):** en `backend/tests/`, casos que disparan `grant_enrollment_from_purchase`/`grant_enrollment_by_email` dos veces (secuencial y con hilos/async) y verifican un solo enrollment + manejo de la excepción de integridad.

### 5.8 (h) Reembolsos y fallos de pago en webhook

- **Estado actual:** `handle_event` (backend/services/stripe.py) no maneja `charge.refunded` ni `checkout.session.async_payment_failed`.
- **Cambio:**
  - `charge.refunded`: localizar la compra por `charge_id`/`payment_intent` y **revocar el enrollment** asociado (o marcarlo `refunded` y revocar acceso).
  - `checkout.session.async_payment_failed`: marcar la compra como fallida (no otorgar enrollment; si se otorgó por error, revocarlo).
  - Idempotencia: procesar cada evento una sola vez (guardar `event_id` procesado o usar el `id` del evento de Stripe como clave única).
- **Impacto:** los reembolsos revocan acceso real; los pagos fallidos no dejan enrollments huérfanos.

### 5.9 (i) Quitar `typescript.ignoreBuildErrors`

- **Estado actual:** `next.config.mjs` tiene `typescript: { ignoreBuildErrors: true }`.
- **Cambio:** eliminar la opción (o fijarla en `false`). El build de producción fallará si hay errores de tipado; el job `frontend-checks` (5.7) los detecta antes.
- **Impacto:** puede requerir corregir errores de tipado existentes al activar; se hace en la misma iteración.

### 5.10 (j) Refresco de URLs pre-firmadas en `VideoPlayer`

- **Estado actual:** `VideoPlayer` obtiene `getStreamUrl(lessonId)` una vez al montar; si la lección dura más de 900s (expiración por defecto de S3), la URL expira durante la reproducción.
- **Cambio:**
  1. `getStreamUrl` devuelve también `expires_at` (timestamp) o el backend expone la expiración.
  2. `VideoPlayer` programa un refresco: cuando falten ~60s para expirar, re-llama `getStreamUrl(lessonId)` y actualiza `src` **sin reiniciar** la reproducción (preservando `currentTime`).
  3. Si la reproducción falla con error de red/403 (URL expirada), reintenta una vez con URL nueva antes de mostrar error.
- **Impacto:** lecciones largas se reproducen sin cortes.

### 5.11 (k) Autenticación en `POST /payments/checkout-session`

- **Estado actual:** `backend/routers/payments.py` define `create_checkout_session` sin dependencia de autenticación; cualquier cliente puede crear una sesión de checkout (deuda detectada por la spec 004, que exige JWT en el padre).
- **Cambio:** añadir `user_id: int = Depends(get_current_user_id)`. El usuario se deriva del token (mismo patrón que `enroll-free` de 004).
- **Impacto:** el checkout exige sesión; sin token → 401 (`HTTPBearer` sin credenciales), token inválido/expirado → 401. El rechazo 400 de cursos gratuitos (004) se mantiene sin cambios.

## 6. Criterios de aceptación

- [ ] (a) `POST /videos/upload-url` devuelve 401 sin token (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)) y 403 para no-admin.
- [ ] (b) `GET /videos/download-url` exige JWT y enrollment; el parámetro `customer_email` desaparece; responde 403 sin enrollment.
- [ ] (c) La app no arranca sin `JWT_SECRET_KEY`; `backend/.env.example` documenta un valor de ejemplo.
- [ ] (d) `lib/products.ts` eliminado; la landing consume `GET /courses`; `PRICE_MAP` eliminado y cada curso tiene su precio/`stripe_price_id`; `CourseId` ya no limita el checkout (cualquier curso activo de la BD es comprable).
- [ ] (e) `backend/Dockerfile` sin `COPY backend/ .env`.
- [ ] (f) Imagen frontend sirve `out/` con nginx; imagen backend corre uvicorn sin `--reload` y con usuario no-root.
- [ ] (g) El workflow ejecuta pytest, lint, `tsc --noEmit` y build de imagen backend antes del deploy.
- [ ] (h) `charge.refunded` revoca el enrollment; `async_payment_failed` marca la compra fallida; eventos idempotentes.
- [ ] (i) El build falla con errores de tipado (opción eliminada).
- [x] (j) `VideoPlayer` refresca la URL antes de expirar sin reiniciar la reproducción (tests vitest 2026-10-01).
- [ ] (k) `POST /payments/checkout-session` devuelve 401 sin token y 401 con token inválido.
- [ ] (g) Existen pruebas de concurrencia/idempotencia de enrollments y pasan.

## 7. Riesgos y consideraciones

- **Orden de implementación:** (c) y (a)/(b) son los más urgentes (seguridad). (d) toca frontend y backend a la vez: hacerlo con cuidado de no romper `/academy` (que ya usa el catálogo real).
- **`next start` vs export estático:** la spec asume mantener `output: "export"` (GitHub Pages). Si el equipo decide migrar a `next start`, (f) cambia y el deploy deja de ser estático — decisión que debe tomarse antes de implementar (f).
- **`stripe_price_id` por curso:** requiere coordinación con el dashboard de Stripe (crear un Price por curso). Mientras no existan, el checkout puede seguir usando el `STRIPE_PRICE_ID` global pero **validando** que `price_cents` coincida con el precio del Price (o documentar la desalineación).
- **Refresco de URL:** cambiar `src` de un `<video>` en reproducción puede causar un parpadeo; probar en navegadores objetivo. Alternativa: precargar la URL nueva y hacer swap solo si la actual falla.
- **CI/CD:** el job de tests backend necesita variables de entorno de prueba (SQLite, `PAYMENTS_MOCK=true`); nunca usar credenciales reales de Stripe/AWS en CI.
- **Webhook idempotente:** guardar `event_id` de Stripe evita doble procesamiento si Stripe reintenta; requiere columna nueva en `purchases` o tabla `webhook_events`.

## 8. Especificación funcional (SDD)

### 8.1 (a) `POST /videos/upload-url` (admin)

- **Entrada:** `{object_key, content_type?}` + token JWT.
- **Salida:** 200 `{upload_url, ...}` (comportamiento actual) o 403.
- **Reglas:** sin token → 401 (`HTTPBearer`); token inválido/expirado → 401 (`get_current_user_id`); token de no-admin → 403 (`require_admin`); admin → URL pre-firmada como hoy.
- **Casos borde:** token expirado → 401; `object_key` vacío → 422; admin con token válido → 200.

### 8.2 (b) `GET /videos/download-url` (JWT + enrollment)

- **Entrada:** `course_id` + token JWT (ya no `customer_email`).
- **Salida:** 200 `{download_url}` si el usuario tiene enrollment; 403 si no; 401 sin token (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- **Reglas:** el usuario se deriva del token; se verifica enrollment activo en el curso; header `Deprecation: true`.
- **Casos borde:** curso inexistente → 404; usuario sin enrollment → 403; token inválido → 401; curso gratuito con enrollment → 200.

### 8.3 (c) `JWT_SECRET_KEY` obligatoria

- **Entrada:** variables de entorno.
- **Salida:** arranque correcto si la variable existe; `ValidationError` al arrancar si falta.
- **Reglas:** sin default; longitud mínima recomendada 32 chars (validación opcional con warning).
- **Casos borde:** variable vacía → error; variable presente → arranca; `.env.example` documenta valor de ejemplo.

### 8.4 (d) Catálogo único

- **Entrada:** `GET /courses` (backend).
- **Salida:** la landing y `/academy` muestran el mismo catálogo.
- **Reglas:** `lib/products.ts` eliminado; `AcademySection`/`CourseDetail` usan `lib/api.ts`; el botón de compra enlaza a `/academy`; `PRICE_MAP` eliminado; cada curso con `price_cents` y `stripe_price_id` propio (nullable); `CheckoutSessionRequest.course_id` pasa de enum `CourseId` a `str` validado contra la BD; `Purchase.course_id` migra de `SqlEnum(CourseId)` a `String`; `COURSE_VIDEO_KEYS` eliminado.
- **Casos borde:** backend caído → la landing muestra estado de error (no datos estáticos obsoletos); curso sin `stripe_price_id` → el checkout usa el global con validación de precio o bloquea la compra (decisión documentada); `course_id` inexistente/inactivo → 404 en checkout; migración del enum de `purchases` en PostgreSQL ya poblada → recrear la columna como `String` preservando filas (ALTER TYPE no permite quitar valores).

### 8.5 (e) `backend/Dockerfile`

- **Entrada:** contexto del repo.
- **Salida:** imagen sin archivo `.env` falso.
- **Reglas:** sin `COPY backend/ .env`; el entorno llega por `env_file`/variables.
- **Casos borde:** build sin `backend/.env` presente → la imagen construye igual (el fallo de arranque por variables faltantes ocurre en runtime, no en build).

### 8.6 (f) Contenedores de producción

- **Entrada:** `Dockerfile.frontend` (multi-stage) y `backend/Dockerfile` (prod).
- **Salida:** imagen frontend sirve `out/` en nginx:80; imagen backend corre uvicorn sin `--reload` con 2 workers y usuario no-root.
- **Reglas:** el stage de build del frontend ejecuta `pnpm build`; el runtime copia solo `out/`; backend: `USER app` después de instalar dependencias.
- **Casos borde:** build sin `NEXT_PUBLIC_API_BASE_URL` → usar default de desarrollo (documentado); puerto expuesto distinto (80 vs 3000) → actualizar `podman-compose.yml`.

### 8.7 (g) CI/CD

- **Entrada:** push a `main`.
- **Salida:** jobs backend-tests, frontend-checks y backend-image pasan antes del deploy.
- **Reglas:** pytest con SQLite de prueba y `PAYMENTS_MOCK=true`; lint y `tsc --noEmit`; build de imagen backend (verificación); deploy depende de los anteriores.
- **Casos borde:** fallo de tests → no deploy; fallo de lint → no deploy; cambios solo de docs → los jobs corren igual (o se optimiza con paths, opcional).

### 8.8 (h) Webhook de reembolsos

- **Entrada:** eventos `charge.refunded` y `checkout.session.async_payment_failed` de Stripe.
- **Salida:** enrollment revocado (refund) o compra marcada fallida; evento registrado como procesado.
- **Reglas:** idempotencia por `event_id`; el refund localiza la compra por `payment_intent`/`charge`; revocar enrollment no elimina el progreso del usuario (solo el acceso).
- **Casos borde:** evento duplicado → se ignora; refund sin compra asociada → log + 200 (no romper el webhook); `async_payment_failed` sin enrollment otorgado → solo marca la compra.

### 8.9 (i) TypeScript estricto en build

- **Entrada:** `next.config.mjs`.
- **Salida:** build falla con errores de tipado.
- **Reglas:** eliminar `typescript.ignoreBuildErrors`; corregir errores existentes en la misma iteración.
- **Casos borde:** errores de tipado en archivos no usados → igual fallan (tsc revisa todo el proyecto); `tsconfig.json` ya tiene `strict: true` (verificado).

### 8.10 (j) Refresco de URL pre-firmada

- **Entrada:** `getStreamUrl(lessonId)` devuelve `{url, expires_at}`.
- **Salida:** `VideoPlayer` refresca `src` antes de expirar sin reiniciar.
- **Reglas:** refresco programado a `expires_at - 60s`; al refrescar, preservar `currentTime`; si el video falla con 403/red, reintentar una vez con URL nueva.
- **Casos borde:** `expires_at` ausente (respuesta vieja) → no programar refresco (compatibilidad); lección corta → el refresco se programa solo desde `expires_at` (a `expires_at - 60s`), así que una lección más corta que la vigencia de la URL termina antes de que el temporizador se dispare; refresco falla → mantener la URL actual sin reprogramar (el reintento único del evento `error` actúa como red de seguridad).

### 8.11 (k) `POST /payments/checkout-session` (JWT)

- **Entrada:** payload `{course_id, ...}` + token JWT.
- **Salida:** 200 con session id (comportamiento actual) o 403/401.
- **Reglas:** sin token → 401 (`HTTPBearer` sin credenciales); token inválido/expirado → 401 (`get_current_user_id`); con token → comportamiento actual (incluido el rechazo 400 de cursos gratuitos de 004).
- **Casos borde:** token expirado → 401; sin token → 401; curso gratuito con token → 400 (regla de 004, sin cambios).

## 9. Casos de prueba (TDD Vanilla)

### (a) upload-url
- `test_upload_url_requires_auth`: Arrange: sin token. Act: `POST /videos/upload-url`. Assert: 401 (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_upload_url_forbidden_for_non_admin`: Arrange: token de usuario normal. Act: `POST /videos/upload-url`. Assert: 403.
- `test_upload_url_allowed_for_admin`: Arrange: token de admin. Act: `POST /videos/upload-url` con `object_key` válido. Assert: 200 con `upload_url`.

### (b) download-url
- `test_download_url_requires_auth`: Arrange: sin token. Act: `GET /videos/download-url?course_id=X`. Assert: 401 (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_download_url_forbidden_without_enrollment`: Arrange: token válido, usuario sin enrollment. Act: `GET /videos/download-url?course_id=X`. Assert: 403.
- `test_download_url_allowed_with_enrollment`: Arrange: usuario con enrollment. Act: `GET /videos/download-url?course_id=X`. Assert: 200 con `download_url` y header `Deprecation: true`.
- `test_download_url_404_for_unknown_course`: Arrange: token válido, curso inexistente. Act: endpoint. Assert: 404.
- `test_download_url_ignores_customer_email_param`: Arrange: petición con `customer_email` en query (parámetro eliminado). Act: endpoint. Assert: el acceso se decide por token, no por el query.

### (c) JWT_SECRET_KEY
- `test_settings_fails_without_jwt_secret`: Arrange: entorno sin `JWT_SECRET_KEY`. Act: instanciar `Settings()`. Assert: `ValidationError`.
- `test_settings_accepts_jwt_secret_when_present`: Arrange: `JWT_SECRET_KEY` de 32+ chars. Act: instanciar. Assert: arranca sin error.

### (d) catálogo único
- `test_landing_academy_section_uses_backend_catalog`: Arrange: mock de `getCourses` con 2 cursos. Act: render `AcademySection`. Assert: muestra los cursos del backend (no `lib/products.ts`).
- `test_products_ts_removed`: Arrange: repo. Act: grep `lib/products.ts` en imports. Assert: 0 resultados.
- `test_price_map_removed`: Arrange: repo. Act: grep `PRICE_MAP` en backend. Assert: 0 resultados.
- `test_checkout_uses_course_specific_price`: Arrange: curso con `stripe_price_id` propio. Act: `POST /payments/checkout-session`. Assert: se usa el `stripe_price_id` del curso (no el global).
- `test_checkout_accepts_course_not_in_old_enum`: Arrange: curso nuevo `mi-curso-nuevo` creado vía admin (fuera del enum `CourseId` original), con `stripe_price_id`. Act: `POST /payments/checkout-session` con `course_id="mi-curso-nuevo"`. Assert: 200 (antes de esta corrección respondía 422 por el enum).
- `test_checkout_404_for_unknown_course_id_string`: Arrange: `course_id` string inexistente en BD. Act: `POST /payments/checkout-session`. Assert: 404 (validación contra la tabla `courses`, ya no contra el enum).
- `test_purchase_course_id_is_plain_string`: Arrange: compra de curso fuera del enum. Act: crear `Purchase` y leerlo. Assert: `course_id` persiste como string sin restricción de enum en BD.

### (e) Dockerfile backend
- `test_backend_dockerfile_has_no_copy_env`: Arrange: leer `backend/Dockerfile`. Act: buscar `COPY backend/ .env`. Assert: no existe la línea.

### (f) contenedores prod
- `test_frontend_dockerfile_serves_static_out`: Arrange: leer `Dockerfile.frontend`. Act: inspeccionar stages. Assert: stage runtime con nginx sirviendo `out/` (sin `pnpm dev`).
- `test_backend_dockerfile_no_reload`: Arrange: leer `backend/Dockerfile`. Act: inspeccionar CMD. Assert: `uvicorn` sin `--reload` y con `--workers`.
- `test_backend_dockerfile_runs_as_non_root`: Arrange: leer `backend/Dockerfile`. Act: buscar `USER`. Assert: existe `USER` no-root.

### (g) CI/CD
- `test_workflow_has_backend_tests_job`: Arrange: leer workflow. Act: buscar `pytest`. Assert: existe job que ejecuta `pytest backend/tests`.
- `test_workflow_has_frontend_lint_and_typecheck`: Arrange: leer workflow. Act: buscar `pnpm run lint` y `pnpm run typecheck`. Assert: ambos presentes.
- `test_workflow_deploy_depends_on_checks`: Arrange: leer workflow. Act: inspeccionar `needs` del job deploy. Assert: depende de backend-tests y frontend-checks.
- `test_grant_enrollment_idempotent_under_concurrency`: Arrange: usuario y curso, dos llamadas concurrentes a `grant_enrollment_by_email`. Act: ejecutar. Assert: un solo enrollment y sin excepción no controlada.
- `test_grant_enrollment_from_purchase_handles_duplicate`: Arrange: compra ya procesada. Act: `grant_enrollment_from_purchase` de nuevo. Assert: idempotente (no duplica enrollment).

### (h) webhook reembolsos
- `test_charge_refunded_revokes_enrollment`: Arrange: compra con enrollment activo, evento `charge.refunded`. Act: `handle_event`. Assert: enrollment revocado y evento registrado.
- `test_async_payment_failed_marks_purchase_failed`: Arrange: compra pendiente, evento `checkout.session.async_payment_failed`. Act: `handle_event`. Assert: compra marcada fallida, sin enrollment.
- `test_webhook_event_processed_once`: Arrange: mismo `event_id` dos veces. Act: `handle_event` dos veces. Assert: el segundo se ignora (idempotente).
- `test_refund_without_purchase_logs_and_returns_ok`: Arrange: `charge.refunded` sin compra asociada. Act: `handle_event`. Assert: 200 (no rompe el webhook) y log de advertencia.

### (i) TypeScript
- `test_next_config_no_ignore_build_errors`: Arrange: leer `next.config.mjs`. Act: buscar `ignoreBuildErrors`. Assert: no existe (o es `false`).
- `test_typecheck_passes_on_clean_code`: Arrange: repo sin errores de tipado. Act: `pnpm run typecheck`. Assert: exit code 0.

### (j) refresco de URL
- `test_video_player_refreshes_url_before_expiry`: Arrange: `getStreamUrl` devuelve `{url, expires_at: now+120s}`, video en reproducción. Act: avanzar 60s (temporizador simulado). Assert: `getStreamUrl` re-invocado y `src` actualizado sin reiniciar (`currentTime` preservado).
- `test_video_player_does_not_refresh_for_short_lessons`: Arrange: `expires_at` a 10 min, lección de 5 min. Act: reproducir la lección completa (avanzar 5 min). Assert: `getStreamUrl` no se re-invoca durante la lección (el refresco se programa solo desde `expires_at`, a `expires_at - 60s` = minuto 9, después de que termine la lección).
- `test_video_player_retries_once_on_expired_url_error`: Arrange: primer `src` falla con 403. Act: disparar error. Assert: `getStreamUrl` re-invocado una vez y `src` reemplazado; si vuelve a fallar, se muestra el estado de error.
- `test_video_player_handles_missing_expires_at`: Arrange: `getStreamUrl` devuelve solo `{url}` (respuesta vieja). Act: montar. Assert: reproduce sin programar refresco (compatibilidad).
- `test_video_player_shows_error_when_initial_load_fails`: Arrange: `getStreamUrl` rechaza al montar. Act: montar. Assert: se muestra el mensaje de error.
- `test_video_player_keeps_current_url_when_refresh_fails`: Arrange: refresco programado que rechaza. Act: avanzar hasta `expires_at - 60s`. Assert: se mantiene la URL actual y no se muestra estado de error.

### (k) checkout-session
- `test_checkout_session_requires_auth`: Arrange: sin token. Act: `POST /payments/checkout-session`. Assert: 401 (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_checkout_session_rejects_invalid_token`: Arrange: token inválido/expirado. Act: `POST /payments/checkout-session`. Assert: 401.
- `test_checkout_session_allowed_with_valid_token`: Arrange: token válido, curso de pago. Act: `POST /payments/checkout-session`. Assert: 200 con session id (comportamiento actual).
