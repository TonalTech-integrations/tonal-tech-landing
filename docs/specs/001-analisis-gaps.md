# 001 - Análisis de gaps: visión (FUNCIONALIDAD.md) vs estado actual (ANALISIS-PROYECTO.md)

- **Estado:** borrador
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

Este documento es la especificación raíz del proyecto: compara la **visión** descrita en `docs/FUNCIONALIDAD.md` (landing B2B con 4 secciones cotizables, Tonal-Tech Labs, Academy con cursos gratuitos y de pago, dashboard oculto de administradores con métricas) contra el **estado actual** documentado en `docs/ANALISIS-PROYECTO.md` (basado en lectura directa del código). De esa comparación se derivan los **gaps** (Total / Parcial / Ninguno), se priorizan y se organizan en un **roadmap de 4 fases** que las specs 002–007 implementan. También consolida los **14 riesgos/deuda técnica** del análisis como trabajo a resolver.

El resultado es la hoja de ruta que un desarrollador debe seguir para llevar la versión actual a la visión, respetando el ciclo iterativo del proyecto (Planificación → Requerimientos → Diseño → Codificación → Pruebas → Deploy → Mantenimiento).

## 2. Objetivos

- Establecer una comparativa trazable entre cada requerimiento de la visión y su estado real en el código.
- Clasificar cada brecha como gap Total, Parcial o Ninguno y asignarle la spec que la cubre.
- Priorizar el trabajo (Alta / Media / Baja) según impacto en el negocio y dependencias técnicas.
- Definir un roadmap de implementación en 4 fases con orden de ejecución y dependencias.
- Consolidar los 14 riesgos de `ANALISIS-PROYECTO.md` como deuda técnica a resolver en la Fase 1.

## 3. Alcance

### Incluye
- Tabla de requerimientos de la visión vs estado actual vs gap vs spec responsable.
- Priorización de cada requerimiento.
- Roadmap de implementación en 4 fases con dependencias.
- Lista de los 14 riesgos/deuda técnica y su spec de resolución.
- Referencias cruzadas a las specs 002–007.

### Excluye
- Detalle de implementación de cada gap (cada spec 002–007 lo cubre).
- Código fuente o migraciones (se definen en las specs individuales).
- Decisiones de negocio sobre precios o contenido de cursos/apps.

## 4. Requisitos

| ID | Requerimiento (visión FUNCIONALIDAD.md) | Estado actual (ANALISIS-PROYECTO.md) | Gap | Spec que lo cubre | Prioridad |
|----|------------------------------------------|--------------------------------------|-----|-------------------|-----------|
| V1 | Landing como entrada principal: cotizar y acceder a Labs y Academy | Landing pública existe (`app/page.tsx`) con las 6 secciones en header/footer y `ServiceGrid` | Ninguno (base) | 001 (base) | Alta |
| V2 | Las 4 secciones cotizables (Optimización Comercial, Arquitectura Cloud, Ciberseguridad, Soporte de Cómputo) con formulario de cotización | `LeadProvider` simulado: `setTimeout(2600ms)` en `components/lead-panel.tsx`, sin backend, sin persistencia | **Total** | 002 | Alta |
| V3 | Cotización generada por IA a partir de lo recolectado y parámetros en BD | No existe infraestructura de IA ni parámetros de cotización en BD | **Total** (futuro, Fase 4) | 002 (diseño desacoplado) | Baja |
| V4 | Derivación a agente humano cuando se requiera | No existe concepto de agente ni de estados de lead | **Total** | 002 | Alta |
| V5 | Labs: listado de desarrollos móviles (con o sin precio) | `labs` solo existe como categoría de servicio en `lib/tonal-data.ts` (tarjeta que abre el panel de leads) y enlaces de header/footer. No hay listado | **Total** | 003 | Media |
| V6 | Labs: al seleccionar una app, abrir info completa, link de descarga y trailer de YouTube | No existe detalle de app, ni descarga, ni trailer | **Total** | 003 | Media |
| V7 | Academy: login para acceder | Auth JWT real: `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Ninguno | 004/005 (mantener) | Alta |
| V8 | Academy: cursos gratuitos o de pago usando Stripe | Solo pago vía Stripe Checkout; `is_free` existe únicamente a nivel de **lección** (`backend/services/persistence.py`), no de curso | **Parcial** | 004 | Alta |
| V9 | Dashboard oculto para administradores | Existen endpoints `/admin/*` (CRUD cursos/módulos/lecciones, enrollments) pero **cero UI** en `app/` (grep `admin` en `app/` = 0 resultados) | **Total** (UI) | 005 | Media |
| V10 | Dashboard: agregar cursos y gestionar tipo pago/gratuito | CRUD de cursos existe en backend; **no** hay campo `is_free` en cursos ni gestión del tipo | **Parcial** | 005 + 004 | Media |
| V11 | Dashboard: métricas de acceso | No existe tracking de visitas (grep `metric/track/visit/analytics` en backend = 0) | **Total** | 006 | Media |
| V12 | Dashboard: saber a qué sección entran más los usuarios | No existe ningún dato de navegación | **Total** | 006 | Media |
| V13 | Ciclo iterativo de desarrollo (Planificación → … → Mantenimiento) | Documentado en FUNCIONALIDAD.md; el proyecto se desarrolla por iteraciones | Ninguno (proceso) | 001 (roadmap) | Alta |

**Resumen de gaps:** 8 requerimientos con gap Total, 2 con gap Parcial, 3 sin gap. El trabajo de mejora se concentra en: cotización B2B (V2, V4), Labs (V5, V6), cursos gratuitos (V8), dashboard admin (V9, V10) y métricas (V11, V12).

## 5. Diseño / Arquitectura

### 5.1 Roadmap de implementación en fases

```
Fase 1 — Fundamentos y deuda crítica        → spec 007
Fase 2 — Cotización manual + Labs + Gratis  → specs 002, 003, 004
Fase 3 — Dashboard admin + Métricas         → specs 005, 006
Fase 4 — IA de cotización                   → spec 008 (extiende 002)
```

#### Fase 1: Fundamentos / deuda crítica (spec 007)
Endurecer la base antes de construir encima. Sin esto, cualquier feature nueva se apoya en backend inseguro, catálogos duplicados y cero pruebas.

- (a) Autenticación en `POST /videos/upload-url` (solo admin).
- (b) Deprecar/reemplazar `GET /videos/download-url` por flujo JWT.
- (c) `JWT_SECRET_KEY` sin default inseguro (obligatoria en producción).
- (d) Unificar catálogos de cursos (`lib/products.ts` vs `COURSE_SEED` del backend).
- (e) Corregir `backend/Dockerfile` (`COPY backend/ .env`).
- (f) Contenedores de producción (build estático + servidor estático; `uvicorn` sin `--reload`).
- (g) CI/CD con tests de backend (pytest) y frontend (lint + `tsc --noEmit`) y build de imagen backend.
- (h) Manejo de reembolsos en webhook (`charge.refunded`, `checkout.session.async_payment_failed`).
- (i) Quitar `typescript.ignoreBuildErrors: true`.
- (j) Refresco de URLs pre-firmadas en `VideoPlayer`.

**Criterio de salida de Fase 1:** CI verde con tests, backend sin endpoints públicos inseguros, catálogo único, contenedores de producción desplegables.

#### Fase 2: Cotización manual + Labs + cursos gratuitos (specs 002, 003, 004)
Funcionalidad visible de negocio sobre una base saneada.

- 002: sistema de leads/cotizaciones B2B manual (persistencia, estados, agente humano, panel de gestión a nivel API) con interfaz de servicio de cotización desacoplada para migrar a IA en Fase 4.
- 003: sección Tonal-Tech Labs (listado de apps, detalle, descarga, trailer YouTube).
- 004: cursos gratuitos en Academy (campo `is_free` en cursos, inscripción sin checkout).

**Criterio de salida de Fase 2:** un lead se persiste y puede cotizarse manualmente; Labs lista apps reales; un curso gratuito se inscribe sin pasar por Stripe.

#### Fase 3: Dashboard admin + Métricas (specs 005, 006)
Gobierno y visibilidad.

- 005: UI de dashboard oculto en `/admin` (JWT + `is_admin`): CRUD de cursos/módulos/lecciones, enrollments manuales, vista de leads/cotizaciones (enlazada con 002).
- 006: métricas de acceso (modelo `PageView`, `POST /metrics/page-view`, `GET /admin/metrics`) y visualización dentro del dashboard (005).

**Criterio de salida de Fase 3:** un admin gestiona cursos y ve leads y métricas desde el navegador.

#### Fase 4: IA de cotización (spec 008)
- Implementar `AIQuoteService` (misma interfaz que `ManualQuoteService` definida en 002): la IA pregunta lo necesario por sección, genera la cotización con parámetros de BD (`quote_pricing_rules`) y deriva a agente humano si se requiere.
- Requiere: parámetros de cotización por servicio en BD (modelo `QuoteParams` ya definido en 002), proveedor de IA configurable vía variable de entorno (`AI_PROVIDER`), y evaluación de calidad de cotizaciones antes de habilitar en producción (`QUOTE_SERVICE=ai`).

### 5.2 Dependencias entre specs

```
007 (Fase 1) ──► 002, 003, 004 (Fase 2) ──► 005, 006 (Fase 3) ──► 008 (Fase 4: IA)
                     │                            │
                     └── 002 provee /admin/leads ──┘ (005 muestra leads)
                     └── 004 agrega is_free ────────┘ (005 gestiona pago/gratuito)
                     └── 003 agrega /labs/apps ─────┘ (006 mide visitas a Labs)

009 (Infraestructura/operación) — TRANSVERSAL: aplica a todas las fases
```

- 005 depende de 002 (vista de leads/cotizaciones) y de 004 (gestión de tipo pago/gratuito).
- 006 depende de 005 (visualización) y de 003/004 (secciones a medir).
- 004 depende de 007(d) (catálogo único) para que el flujo gratuito use el mismo catálogo en landing y Academy.
- 008 depende de 002 (interfaz `QuoteService`, modelo `QuoteParams`) y de 005 (edición de preguntas/reglas desde el dashboard).
- 009 depende de 007(e, f, g) (imágenes y pipeline corregidos) y habilita el despliegue real de todas las demás: sin servidor/ambientes definidos, 002–008 solo son operables en local.

### 5.3 Deuda técnica consolidada (14 riesgos de ANALISIS-PROYECTO.md)

| # | Riesgo / deuda | Spec que lo resuelve |
|----|----------------|----------------------|
| 1 | Cero pruebas automatizadas en el repositorio | 007 (g) |
| 2 | Dos catálogos de cursos desincronizados (`lib/products.ts` vs `COURSE_SEED`) | 007 (d) |
| 3 | `POST /videos/upload-url` sin autenticación | 007 (a) |
| 4 | `GET /videos/download-url` sin JWT (solo email+course_id en query) | 007 (b) |
| 5 | `JWT_SECRET_KEY` con default inseguro hardcodeado | 007 (c) |
| 6 | `backend/Dockerfile` con `COPY backend/ .env` | 007 (e) |
| 7 | Contenedores en modo desarrollo (`pnpm dev`, `uvicorn --reload`) | 007 (f) |
| 8 | CI/CD solo frontend, sin tests ni backend | 007 (g) |
| 9 | Sin manejo de reembolsos (`charge.refunded`, `async_payment_failed`) | 007 (h) |
| 10 | `typescript.ignoreBuildErrors: true` | 007 (i) |
| 11 | Validación de email del lead solo en cliente | 002 (validación servidor) |
| 12 | Sin tests de concurrencia/idempotencia en enrollments | 007 (g) + 004 |
| 13 | `PRICE_MAP` usa el mismo `STRIPE_PRICE_ID` para los 3 cursos | 007 (d) |
| 14 | URLs pre-firmadas de 900s pueden expirar en lecciones largas | 007 (j) |

## 6. Criterios de aceptación

- [ ] Existe una tabla que mapea cada requerimiento de FUNCIONALIDAD.md a su estado actual, gap y spec responsable.
- [ ] Cada gap Total/Parcial tiene al menos una spec (002–007) que lo cubre explícitamente.
- [ ] El roadmap define 4 fases con criterios de salida y dependencias entre specs.
- [ ] Los 14 riesgos de ANALISIS-PROYECTO.md están mapeados a una spec de resolución.
- [ ] La Fase 4 (IA) queda declarada como alcance futuro con el diseño desacoplado ya previsto en 002 y especificada en 008.
- [ ] El documento es consistente con el estado real del código (no inventa funcionalidad existente).

## 7. Riesgos y consideraciones

- **Orden de fases:** implementar 005/006 antes de 007 duplicaría deuda (p. ej., catálogos desincronizados afectarían al dashboard). La Fase 1 es prerrequisito recomendado, no bloqueante: si el negocio exige visibilidad temprana, 002/003/004 pueden iniciarse en paralelo con 007 siempre que los endpoints nuevos ya nazcan con autenticación y pruebas.
- **Export estático:** el frontend usa `output: "export"` (GitHub Pages). Las rutas protegidas (`/admin`) solo pueden protegerse en cliente; la seguridad real debe vivir en los endpoints del backend (ya protegidos con `is_admin`). Esto se documenta en 005.
- **`next start` vs export estático:** con `output: "export"` no existe `next start`; el contenedor de producción debe servir `out/` con un servidor estático (nginx o similar). La spec 007(f) lo aclara.
- **IA (Fase 4):** no se debe iniciar hasta que el flujo manual (002) esté operando y acumule datos reales de cotizaciones para calibrar la IA.
- **Métricas:** el tracking de visitas debe respetar privacidad (sin PII innecesaria) y considerar limitación de tasa para evitar ruido/abuso (ver 006).

## 8. Especificación funcional (SDD)

### Funcionalidad: proceso de mejora por fases

- **Entrada:** visión (FUNCIONALIDAD.md), estado actual (ANALISIS-PROYECTO.md), código del repositorio.
- **Salida:** conjunto de specs 002–007 accionables, ordenadas en fases.
- **Reglas de negocio:**
  - Cada spec debe ser implementable sin ambigüedad por un desarrollador.
  - Ninguna spec puede inventar funcionalidad que no exista o no esté planificada en la visión.
  - La Fase 4 (IA) solo se habilita después de la Fase 2 (manual) operando.
- **Casos borde:**
  - Un requerimiento de la visión sin gap (V1, V7, V13) no genera spec nueva; se mantiene y se protege con pruebas (007).
  - Un gap parcial (V8, V10) genera spec que extiende lo existente sin romperlo (004, 005).
  - Deuda técnica sin requerimiento de visión explícito (riesgos 1–14) se resuelve en 007.

## 9. Casos de prueba (TDD Vanilla)

- `test_every_vision_requirement_has_gap_and_spec`: Arrange: lista de requerimientos V1–V13. Act: recorrer la tabla de la sección 4. Assert: cada requerimiento tiene estado actual, gap y spec responsable no vacíos.
- `test_every_total_gap_has_dedicated_spec`: Arrange: requerimientos con gap Total (V2, V3, V4, V5, V6, V9, V11, V12). Act: verificar referencias a specs. Assert: cada uno referencia al menos una spec 002–007.
- `test_all_14_risks_mapped_to_spec`: Arrange: lista de 14 riesgos. Act: recorrer la tabla 5.3. Assert: cada riesgo tiene una spec de resolución.
- `test_roadmap_phases_are_ordered_by_dependency`: Arrange: fases 1–4. Act: verificar dependencias (007 → 002/003/004 → 005/006 → IA). Assert: ninguna fase depende de una fase posterior.
- `test_ai_phase_marked_as_future_scope`: Arrange: sección 5.1. Act: buscar "Fase 4". Assert: la IA está declarada como alcance futuro y no como parte de la Fase 2.
