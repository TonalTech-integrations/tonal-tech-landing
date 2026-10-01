# COMPACT — tonal-tech-landing (contexto mínimo para restaurar sesión)

**Fecha:** 2026-10-01 · **Proyecto:** `/home/idi_001/Documents/Proyects/Tona/tonal-tech-landing` · Detalle completo en `docs/HANDOFF.md`.

## Qué es
Plataforma B2B de Tonal-Tech: landing (Next.js 16, export estático → GitHub Pages) + API (FastAPI + PostgreSQL/SQLite + Stripe + S3). Visión: 4 secciones cotizables + Labs (apps móviles) + Academy (cursos tipo Udemy) + dashboard admin oculto. Metodología: **SDD + TDD Vanilla**, ciclo iterativo.

## Estado
- Fase: Codificación. **Spec 007 cerrada (a–k)**: backend con 38 tests pytest, ESLint, Dockerfiles prod, CI; el 2026-10-01 se añadió vitest + 11 tests de frontend (`VideoPlayer`, `AcademySection`, `CourseDetail`) y `pnpm test` en el CI (ver HANDOFF §6.1).
- `docs/ANALISIS-PROYECTO.md` = análisis del estado real (14 deudas técnicas).
- `docs/specs/001..009` = specs generadas y **revisadas contra el código real** (aprobadas: 007 el 2026-09-29; 002 y 003 el 2026-10-01; el resto en `borrador`).
- **002 en codificación:** 002-01 (`POST /leads`) y 002-03 (`GET /admin/leads/{id}`) implementadas con TDD — modelos `Lead`/`Quote`/`QuoteParams`, 28 tests nuevos, 66/66 backend pasan. Siguiente: 002-04 (`PATCH /admin/leads/{id}`).
- Roadmap (001): F1 → 007 endurecimiento · F2 → 002 leads manuales + 003 Labs + 004 cursos gratuitos · F3 → 005 dashboard + 006 métricas · F4 → 008 IA de cotización · 009 infraestructura es transversal.

## Restricción vigente
**Solo editar archivos dentro de este proyecto.** Leer fuera (p. ej. `GPI/init_hub/docs/specs/`) está permitido; editar fuera, no.

## Hallazgos críticos (no olvidar)
1. Enum `CourseId` (3 valores) bloquea el checkout de cualquier curso creado por admin → arreglo en spec 007(d) (`course_id: str`, `Purchase.course_id` a String, eliminar `COURSE_VIDEO_KEYS`).
2. Bug preset lead-panel: `openLead(service.title)` no coincide con `serviceCategoriesForm` en 2/4 servicios → mapear por `id` (spec 002).
3. Auth: **401** = sin credenciales (`HTTPBearer`, comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima) y token inválido/expirado (`get_current_user_id`); **403** = usuario no admin o sin permiso. Specs ya corregidas.
4. `GET /admin/courses` no existe; `DELETE /admin/enrollments` usa query `email`+`course_id`; delete de curso con enrollments → 409 (ya implementado).
5. Backend **sin servidor de producción definido** (bloqueo físico, decisión del usuario — 009 §7).

## Siguiente paso
Continuar la spec **002** con TDD (002-02 `GET /admin/leads` con filtros/paginación, ver HANDOFF §6.2); después 003 (Labs). Primero los tests de la sección 6 de cada sub-spec.

## Verificación rápida
```bash
cd /home/idi_001/Documents/Proyects/Tona/tonal-tech-landing
ls docs/specs/          # 001..009
pnpm typecheck          # frontend
pnpm test               # 11 tests frontend (vitest)
.venv/bin/python -m pytest backend/tests -q   # 66 tests backend
```

## Notas
- Leads aceptan **6** categorías (4 cotizables + `labs`/`academy`).
- 008 (IA) reutiliza la interfaz `QuoteService` de 002; activación por `QUOTE_SERVICE=manual|ai`.
- `vite.config.ts` abierto en el IDE es un buffer fantasma: **no existe en disco** (proyecto Next.js).
