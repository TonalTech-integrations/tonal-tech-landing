# 004-01 - Campo is_free en curso (modelo y exposición en catálogo)

- **Spec padre:** [004 - Academy: soporte de cursos gratuitos](../../004-academy-cursos-gratuitos.md) (secciones: 5.1, 5.2, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** Ninguna
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_academy_campo_is_free.py`

## 1. Descripción

Agrega el concepto de curso gratuito completo al backend: columna `is_free` (bool, default `False`) en la tabla `courses`, actualización de `COURSE_SEED` (al menos 1 curso gratuito de ejemplo) y exposición de `is_free` en `CourseSummary` y `CourseDetailResponse` (`GET /courses` y `GET /courses/{id}`). El `is_free` de lección se mantiene: en cursos de pago permite lecciones de muestra sin inscripción; en cursos gratuitos es irrelevante (todas accesibles con enrollment).

**Estado actual verificado en código:** `COURSE_SEED` (`backend/services/persistence.py`) hoy NO tiene ningún curso gratuito: los 3 cursos del seed tienen `price_cents` > 0 (`14900`, `18900`, `12900`) y la tabla `courses` no tiene columna `is_free` (solo `course_lessons` la tiene).

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R1 | La tabla `courses` tiene `is_free` (bool, default `False`) | Alta |
| R2 | `GET /courses` y `GET /courses/{id}` exponen `is_free` en la respuesta | Alta |
| R6 | Un curso gratuito no requiere `STRIPE_PRICE_ID` para inscribirse | Media |
| R10 | El seed incluye al menos un curso gratuito de ejemplo | Media |

## 3. Diseño

**Modelo (5.1, backend/services/persistence.py):**
- **Tabla `courses`:** nueva columna `is_free` (Boolean, default `False`, no nula).
- **`COURSE_SEED`:** agregar `is_free` a cada curso; al menos uno con `is_free=True` y `price_cents=0` (ej. un curso introductorio). La regla de coherencia `is_free=True` ⇒ `price_cents=0` (y viceversa) está confirmada y documentada en el padre (5.1, R11); el seed usa `is_free=True` con `price_cents=0`.
- **Regla de negocio de acceso:** para un curso con `is_free=True`, `has_access = usuario autenticado AND tiene enrollment` (igual que un curso pagado con enrollment). La diferencia es **cómo se obtiene el enrollment**: automático (enroll-free) en lugar de compra.
- El `is_free` de **lección** se mantiene: en cursos de pago permite lecciones de muestra sin inscripción; en cursos gratuitos es irrelevante (todas accesibles con enrollment).

**Endpoints (5.2):**
- `GET /courses` (opcional): `CourseSummary` incluye `is_free`.
- `GET /courses/{course_id}` (opcional): `CourseDetailResponse` incluye `is_free`.

## 4. Especificación funcional (SDD)

- **Entrada:** consulta del catálogo (`GET /courses`) o del detalle (`GET /courses/{course_id}`).
- **Salida:** `CourseSummary`/`CourseDetailResponse` con `is_free` correcto.
- **Reglas:** `is_free` (bool, default `False`) en `courses`; `CourseSummary` y `CourseDetailResponse` exponen `is_free` (5.1/5.2).
- **Casos borde:** migración de BD con cursos existentes → `is_free=False` por default (no rompe filas, no cambia precios ni acceso); seed con al menos un curso `is_free=True` y `price_cents=0`; la regla de coherencia `is_free=True` ⇒ `price_cents=0` (y viceversa) está confirmada en el padre (5.1, R11).

## 5. Criterios de aceptación

- [ ] `courses.is_free` existe con default `False` y el seed tiene al menos un curso gratuito (`is_free=True`, `price_cents=0`).
- [ ] `GET /courses` y `GET /courses/{id}` incluyen `is_free`.
- [ ] Los cursos existentes (migración) quedan con `is_free=False` sin cambios de precio ni de acceso.

## 6. Casos de prueba (TDD Vanilla)

- `test_course_list_includes_is_free_flag`: Arrange: curso gratuito y curso de pago. Act: `GET /courses`. Assert: cada `CourseSummary` incluye `is_free` correcto.
- `test_course_detail_includes_is_free_flag`: Arrange: curso gratuito. Act: `GET /courses/{id}`. Assert: `is_free=True` en la respuesta.
- `test_course_seed_includes_free_course`: Arrange: BD recién inicializada con `seed_courses()`. Act: `GET /courses`. Assert: al menos un curso con `is_free=True` y `price_cents=0`.
- `test_existing_courses_default_to_is_free_false_on_migration`: Arrange: BD con cursos existentes (sin columna `is_free`). Act: migración (agregar columna con default `False`). Assert: todos los cursos existentes quedan con `is_free=False` y conservan `price_cents` y acceso.

## 7. Riesgos y consideraciones

- **Migración de BD:** agregar columna con default no rompe filas existentes; el seed debe actualizarse. Si se usa SQLite en desarrollo, la migración es recreación de tablas (patrón existente del proyecto).
- **`STRIPE_PRICE_ID`:** un curso gratuito no necesita precio de Stripe; `PRICE_MAP` (riesgo #13) no debe consultarse para cursos gratuitos.
- **Regla de coherencia `is_free <-> price_cents` (decisión confirmada):** `is_free=True` ⇒ `price_cents=0` (y viceversa), documentada en el padre (5.1, R11). El seed usa `is_free=True` con `price_cents=0`.
- **Validación admin (diferida a 005):** el padre excluye la gestión del tipo pago/gratuito desde el dashboard admin (lo cubre la spec 005). La validación de crear un curso `is_free=True` con `price_cents>0` (422 u otra regla) se definirá en 005 una vez confirmada la regla de coherencia; no se añade como caso TDD aquí para no contradecir el alcance del padre.
