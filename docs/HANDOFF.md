# Handoff — tonal-tech-landing

- **Fecha del handoff:** 2026-10-01 (creado 2026-09-24)
- **Propósito:** Retomar el trabajo en otra sesión sin perder contexto.
- **Autor del proyecto:** Erick Marin

## 0. ATENCIÓN — Estado actual (leer primero)

**Fase del ciclo:** **Codificación de la spec 002** (leads y cotizaciones B2B), aprobada junto con la 003 el 2026-10-01. **002-01/02/03 ya implementadas** con TDD (28 tests nuevos; 66/66 backend pasan). Siguiente: 002-04 (`PATCH /admin/leads/{id}` — transiciones de estado y asignación de agente). Metodología SDD + TDD Vanilla.

**Restricción de sesión vigente (fijada por el usuario el 2026-09-24):** solo se puede **editar** archivos dentro de `/home/idi_001/Documents/Proyects/Tona/tonal-tech-landing`. Se pueden **leer** archivos de otros proyectos pero nunca editarlos.

Qué se hizo (2026-09-24 a 2026-09-29):

1. Análisis (`docs/ANALISIS-PROYECTO.md`, 14 riesgos) y 9 specs revisadas contra el código.
2. Sub-specs de `docs/specs/specs_funcionalidad/` (002, 003, 004) afinadas y decisiones confirmadas propagadas a los padres. Sin credenciales los endpoints responden **401** (FastAPI>=0.122); 403 solo para no-admin o sin inscripción.
3. **Spec 007 implementada (ítems a–k):**
   - Backend: `backend/tests/` con 38 tests (pytest, SQLite temporal; `backend/requirements-dev.txt`); `CourseId` enum eliminado (`course_id: str` validado contra la tabla `courses`, `stripe_price_id` por curso); JWT obligatorio en `checkout-session` y `download-url` (deprecado), admin en `upload-url`; `JWT_SECRET_KEY` sin default; webhook con `charge.refunded`, `async_payment_failed` e idempotencia por `event_id`; `stream-url` devuelve `expires_at`.
   - Contenedores: `backend/Dockerfile` (sin `.env` falso, sin `--reload`, 2 workers, no-root, healthcheck); `Dockerfile.frontend` multi-stage con nginx (`nginx.conf`, basePath `/tonal-tech-landing`); imágenes construidas y probadas con docker.
   - Frontend: `lib/products.ts` eliminado (landing consume el backend); ESLint 9 añadido (`eslint.config.mjs`, 0 errores/0 avisos); `ignoreBuildErrors` eliminado; `VideoPlayer` refresca la URL pre-firmada.
   - CI: `.github/workflows/deploy.yml` con jobs `backend-tests`, `frontend-checks`, `backend-image`; deploy depende de los tres (no ejecutado aún en GitHub).
   - Migración PostgreSQL verificada contra `postgres:16` real. `SQLAlchemy<2.1` fijado (2.1 usa psycopg v3).
4. **007 cerrada (2026-10-01):** tests de frontend con vitest 3 + vite 6 (fijados por el Node 18 local; vitest 4/vite 7 exigen Node 20+) + testing-library. `vitest.config.ts`, `vitest.setup.ts`, script `pnpm test`; `video-player.test.tsx` (6 casos de §9(j)), `academy-section.test.tsx` (2, incluido `test_landing_academy_section_uses_backend_catalog` de 007(d)) y `course-detail.test.tsx` (3). **11/11 tests pasan**; lint y typecheck en 0. El job `frontend-checks` del CI ahora ejecuta `pnpm test` (aún sin correr en GitHub).
5. **002 y 003 aprobadas (2026-10-01)** con 4 decisiones registradas en 002 §5.3/§7: `quote_params` se crea con el lead (`version=1`); tests de frontend colocados (`components/*.test.tsx`, no `__tests__/`); tras 003 la tarjeta Labs navega a `/labs` y deja de abrir el panel; orden: 002 completa antes que 003.
6. **002-01 implementada (2026-10-01):** `POST /leads` público (`backend/routers/leads.py`); modelos `Lead` y `QuoteParams` en `persistence.py` (`status` como String, no enum nativo — lección de `purchasestatus`); schemas `LeadCreate`/`LeadCreatedResponse` en `backend/schemas.py` (`SERVICE_CATEGORIES`, `COMPANY_SIZES`); respuesta sin `message` ni `assigned_agent_id`. 12 tests en `backend/tests/test_leads_crear_lead_publico.py`. Para correr pytest en esta máquina se creó `.venv/` en la raíz (python3.12; añadido a `.gitignore`): `.venv/bin/python -m pytest backend/tests -q`.
7. **002-02 implementada (2026-10-01):** `GET /admin/leads` con filtros combinables (`status`, `service_category`, rango `from`/`to` por `created_at`), paginación (`page`/`page_size`, máx. 100 → 422) y orden `created_at desc`. `list_leads()` en `persistence.py` (con `func.count` para `total`), `admin_router` (prefijo `/admin`) en `backend/routers/leads.py` reutilizando `require_admin` del router admin. 10 tests en `backend/tests/test_leads_listar_admin.py` (incluye caso borde `page` fuera de rango → lista vacía). **60/60 backend pasan**.

## 1. ¿Qué es el proyecto?

Landing page + plataforma B2B de **Tonal-Tech** (empresa de tecnología). Es la entrada principal de clientes: cotización de 4 líneas de servicio (Optimización Comercial y Analítica, Arquitectura Cloud, Ciberseguridad y Cumplimiento, Soporte de Cómputo), escaparate de apps propias (Labs) y plataforma de cursos tipo Udemy (Academy, gratuitos y de pago con Stripe), más un dashboard oculto de administración. La cotización arranca **manual** y migra a **IA** por fases.

## 2. Ubicación y entorno

- **Ruta base:** `/home/idi_001/Documents/Proyects/Tona/tonal-tech-landing`
- **Entorno:** WSL2 (Linux), bash. **Sí es repositorio git** (tiene `.git/`).
- **Stack:** Next.js 16.3 + React 19 + TS estricto (frontend, **export estático** a GitHub Pages) · FastAPI + SQLAlchemy + Pydantic v2 (backend) · PostgreSQL prod / SQLite dev · Stripe Checkout + webhooks · AWS S3 (URLs pre-firmadas) · Docker/Podman.

### Estructura relevante

```
tonal-tech-landing/
├── docs/
│   ├── FUNCIONALIDAD.md          ← visión del usuario (insumo, no es spec)
│   ├── ANALISIS-PROYECTO.md      ← análisis SDD+TDD del estado actual (14 deudas)
│   ├── HANDOFF.md                ← este documento
│   ├── COMPACT.md                ← versión ultra-resumida para restaurar contexto
│   └── specs/
│       ├── 001-analisis-gaps.md              ← matriz visión-vs-realidad + roadmap 4 fases
│       ├── 002-cotizacion-b2b.md             ← leads/cotización manual (REVISADA ✓)
│       ├── 003-tonal-labs.md                 ← sección Labs (REVISADA ✓)
│       ├── 004-academy-cursos-gratuitos.md   ← cursos gratuitos (REVISADA ✓)
│       ├── 005-dashboard-admin.md            ← dashboard /admin (REVISADA ✓)
│       ├── 006-metricas-acceso.md            ← tracking de visitas (REVISADA ✓)
│       ├── 007-endurecimiento-seguridad.md   ← deuda técnica/seguridad (REVISADA ✓)
│       ├── 008-ia-cotizacion.md              ← Fase 4: cotización por IA (REVISADA ✓)
│       └── 009-infraestructura-despliegue-operacion.md ← ambientes, deploy, ops (REVISADA ✓)
├── app/         (Next.js: page.tsx landing, academy/, success/; NO hay /admin ni /labs)
├── components/  (lead-panel.tsx, service-grid.tsx, site-header.tsx, academy/*, ...)
├── backend/     (FastAPI: main.py, config.py, schemas.py, routers/{auth,courses,payments,videos,admin}.py,
│                 services/{persistence,stripe,storage}.py — 5 tablas + enrollments/purchases/progress)
├── lib/         (api.ts cliente HTTP+JWT, tonal-data.ts; products.ts eliminado en 007(d))
├── Dockerfile.frontend / backend/Dockerfile / podman-compose.yml  (endurecidos en 007(f): nginx sirve out/, uvicorn sin --reload, no-root)
└── .github/workflows/deploy.yml  (jobs: backend-tests, frontend-checks [lint+typecheck+test], backend-image; deploy depende de los tres)
```

## 3. Decisiones ya tomadas

- **Metodología:** SDD (spec antes que código) + TDD Vanilla (tests AAA, sin frameworks BDD). Ciclo iterativo: Planificación → Requerimientos → Diseño → Codificación → Pruebas → Deploy → Mantenimiento.
- **Formato de specs:** el TEMPLATE del proyecto GPI (Resumen / Objetivos / Alcance / Requisitos / Diseño / Criterios de aceptación / Riesgos) + secciones "Especificación funcional (SDD)" y "Casos de prueba (TDD Vanilla)".
- **Roadmap en 4 fases** (spec 001): F1 fundamentos (007) → F2 cotización manual + Labs + cursos gratuitos (002, 003, 004) → F3 dashboard + métricas (005, 006) → F4 IA de cotización (008). **009 es transversal** (ambientes/deploy/operación).
- **La migración manual→IA está diseñada desacoplada:** interfaz `QuoteService` con `ManualQuoteService` (F2) e `AIQuoteService` (F4), selección por `QUOTE_SERVICE=manual|ai` (spec 002 §5.2 / 008 §5.1).
- **Leads aceptan 6 categorías** (4 cotizables + `labs`/`academy` como consulta general — corrección del 2026-09-24, porque el formulario real ofrece las 6).
- **Backend para datos de Labs** (no estáticos), justificado en spec 003 §5.
- **Numeración:** 008 = IA de cotización (ya ocupado); infraestructura quedó en **009** (el usuario tenía un borrador sin guardar llamado `008-infraestructura-...`).

## 4. Hallazgos críticos de la revisión (2026-09-24) — no perderlos

1. **Enum `CourseId` bloquea vender cursos nuevos (CRÍTICO):** `CheckoutSessionRequest.course_id` es un enum de 3 valores fijos (`backend/schemas.py`), `Purchase.course_id` es `SqlEnum(CourseId)` en BD y `COURSE_VIDEO_KEYS` está hardcodeado en `services/stripe.py`. **Ningún curso creado por el admin puede comprarse hoy** (422 por enum). Corrección asignada a spec **007(d)**: `course_id: str` validado contra BD, migrar `Purchase.course_id` a `String`, eliminar `COURSE_VIDEO_KEYS`.
2. **Bug de preset en el panel de leads:** `ServiceGrid` llama `openLead(service.title)` pero 2 de 4 títulos no coinciden con `serviceCategoriesForm` (p. ej. "Ciberseguridad Avanzada y Cumplimiento" ≠ "Ciberseguridad Avanzada") → el pill preseleccionado no se activa. Spec **002** manda mapear por `id` de servicio.
3. **Códigos de auth (recurrente en las specs):** `HTTPBearer` de FastAPI responde **401** sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima); **401** también lo lanza `get_current_user_id` con token inválido/expirado; **403** queda solo para usuario no admin o sin permiso. Todos los tests y criterios ya están corregidos.
4. **`GET /admin/courses` no existe** (admin.py solo tiene POST/PATCH/DELETE de cursos) — el dashboard (005) debe crearlo; `GET /courses` público no sirve porque filtra inactivos.
5. **`DELETE /admin/enrollments` usa query params `email`+`course_id`** (no `enrollment_id`); email inexistente → 404 (no crea usuario). Eliminar curso con enrollments → **409** (ya implementado).
6. **`lib/api.ts#apiFetch`** asume `detail` string: con 422 de Pydantic (lista) mostraría `[object Object]` — spec 002 exige normalizarlo.
7. **`vite.config.ts` fantasma:** apareció abierto en el IDE pero **no existe en disco** (proyecto Next.js, no Vite) — era un buffer sin guardar; ignorarlo.

### Deuda ya conocida (del análisis, cubierta por 007)

`POST /videos/upload-url` sin auth · `GET /videos/download-url` por email+course_id sin JWT · `JWT_SECRET_KEY` con default inseguro · `backend/Dockerfile` con `COPY backend/ .env` (literal) · contenedores en modo dev (`pnpm dev`, `uvicorn --reload`) · CI solo frontend sin tests · `PRICE_MAP` con un solo `STRIPE_PRICE_ID` para 3 cursos · `lib/products.ts` vs `COURSE_SEED` desincronizados (IDs y precios distintos) · `typescript.ignoreBuildErrors: true` · `grant_enrollment` check-then-insert no seguro bajo concurrencia · URLs pre-firmadas de 900 s pueden expirar en lecciones largas · sin manejo de reembolsos en webhook · **cero pruebas automatizadas en todo el repo**.

## 5. Estado de las specs

| Spec | Tema | Estado |
|------|------|--------|
| 001 | Matriz de gaps visión-vs-realidad + roadmap 4 fases | borrador, revisada ✓ |
| 002 | Leads y cotización B2B manual (base para IA) | aprobada 2026-10-01 · 002-01/02/03 implementadas, resto en codificación |
| 003 | Labs (listado apps, detalle, YouTube, descarga) | aprobada 2026-10-01 (pendiente de codificar; va después de 002) |
| 004 | Cursos gratuitos en Academy | borrador, revisada ✓ |
| 005 | Dashboard admin `/admin` (UI completa) | borrador, revisada ✓ |
| 006 | Métricas de acceso (tracking + dashboard) | borrador, revisada ✓ |
| 007 | Endurecimiento y calidad (11 ítems a–k) | aprobada 2026-09-29 · **implementada completa** 2026-10-01 |
| 008 | Cotización por IA (Fase 4) | borrador, revisada ✓ |
| 009 | Infraestructura, despliegue y operación | borrador, revisada ✓ |

**Aprobadas: 007 (2026-09-29), 002 y 003 (2026-10-01).** Las demás siguen en `borrador`. La aprobación del usuario es el gate antes de Codificación.

## 6. Próximo paso al retomar

### 6.1 HECHO (2026-10-01): vitest + tests de frontend

- Instalados: `vitest@^3`, `vite@^6` (fijados por el Node 18 local — vitest 4/vite 7 exigen Node 20+; en CI corre con Node 22 sin cambios), `@vitejs/plugin-react@^4`, `jsdom@^26`, `@testing-library/{react,dom,jest-dom,user-event}`. Ojo: `@vitejs/plugin-react@4` no puede cargar vite 7 (ESM puro), por eso `vite` queda fijado a `^6` como devDependency explícita.
- Creados `vitest.config.ts` (jsdom, alias `@` → raíz, `setupFiles`) y `vitest.setup.ts` (jest-dom + `IS_REACT_ACT_ENVIRONMENT` para React 19); script `"test": "vitest run"` en `package.json`.
- `components/academy/video-player.test.tsx`: 6 casos (los 4 de la spec 007 §9(j) + error al montar + refresco fallido mantiene la URL). jsdom no implementa `HTMLMediaElement`: `currentTime` mutable y `play()` mockeados vía `Object.defineProperty`; `vi.useFakeTimers()` en todos los tests del player.
- `academy-section.test.tsx` (2 casos, incluido `test_landing_academy_section_uses_backend_catalog` que cerraba el pendiente de 007(d)) y `course-detail.test.tsx` (3 casos: render de módulos/lecciones, error/reintento, cierre con Escape).
- Redacción de §8.10/§9(j) de la spec 007 ajustada a la semántica real (el refresco se programa solo desde `expires_at`); criterio (j) marcado como cumplido.
- CI: `frontend-checks` ejecuta `pnpm test` tras lint/typecheck.
- Verificado 2026-10-01 en esta máquina: `pnpm test` → 11/11, `pnpm run lint` y `pnpm typecheck` → 0 errores/avisos.

### 6.2 EN CURSO: codificar la spec 002 (sub-specs restantes)

- **002 y 003 aprobadas (2026-10-01)**; orden acordado: completar 002 antes de empezar 003. 004 requiere el ajuste `is_free` (BD) y 005 es la UI admin (incluye `is_free`/`stripe_price_id` en formularios de curso).
- **Hecho:** 002-01 (`POST /leads`, 12 tests), 002-02 (`GET /admin/leads`, 10 tests; `list_leads()`, `admin_router`, `from`/`to` como `Query(alias=...)`) y 002-03 (`GET /admin/leads/{id}`, 6 tests; `Quote`/`QuoteResponse`/`QuoteParamsResponse`/`LeadDetailResponse` con `from_attributes`, `get_lead_quote`/`get_lead_quote_params`). **Corrección aplicada (002-03):** la sub-spec decía "sin cotización → `quote_params: null`", pero todo lead nace con `quote_params` v1 (decisión §5.3) — corregido en la sub-spec y en el padre: sin cotización → `quote: null` con `quote_params` presente; ambos `null` solo en legado.
- **Siguiente sub-spec:** 002-04 (transiciones/asignación, `PATCH /admin/leads/{id}`), luego 002-05 (crear cotización + `Quote`/`ManualQuoteService`), 002-06 (consultar cotización), 002-07/08/09 (frontend: `LeadProvider` real, mapeo por id, normalización de errores 422 en `apiFetch`).
- Seguir TDD Vanilla: primero los casos de la sección 6 de cada sub-spec, luego el código. Fase 2 del roadmap de 001.
- **Bloqueo físico de Fase 1/009:** el backend **no tiene servidor de producción** (decisión del usuario, 009 §7).
- Limitaciones conocidas: la API admin aún no permite configurar `stripe_price_id` por curso (cae al `STRIPE_PRICE_ID` global); `CourseDetail` de la landing ya no muestra "Lo que aprenderás" (el backend no lo expone); la columna `webhook type` se guarda pero no se consulta; el CI no se ha ejecutado en GitHub.

### Comandos de verificación rápida

```bash
cd /home/idi_001/Documents/Proyects/Tona/tonal-tech-landing
ls docs/specs/                    # deben existir 001..009
pnpm typecheck                    # frontend (script en package.json)
pnpm run lint                     # 0 errores/0 avisos
pnpm test                         # 11 passed a 2026-10-01 (vitest)
# backend: venv local en .venv/ (raíz, ignorado por git); recrear con: python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/python -m pytest backend/tests -q   # 66 passed a 2026-10-01
```

## 7. Cómo retomar esta sesión

Al volver, indicar: *"Retomamos tonal-tech-landing"* y referenciar este archivo (`docs/HANDOFF.md`). Si solo se necesita contexto mínimo, leer `docs/COMPACT.md`.

**Orden de lectura sugerido:** 001 (mapa completo) → la spec que se vaya a implementar → `docs/ANALISIS-PROYECTO.md` §6 (los 14 riesgos).

**Referencias cruzadas:** las specs 002–009 se citan entre sí; si se modifica una, revisar las que la referencian (p. ej. 002 es base de 005, 006 y 008).
