# 004-04 - CourseViewer y AcademyPage (frontend de cursos gratuitos)

- **Spec padre:** [004 - Academy: soporte de cursos gratuitos](../../004-academy-cursos-gratuitos.md) (secciones: 5.3, 8.3, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Frontend
- **Dependencias:** 004-01 (el campo `is_free` expuesto en el catálogo/detalle); 004-02 (el endpoint `enroll-free` que llama `enrollFree`)
- **Suite de pruebas sugerida:** Sugerida: `__tests__/academy/course-viewer.test.tsx`

## 1. Descripción

UI de Academy para cursos gratuitos: `AcademyPage` muestra "Gratis" en las tarjetas del catálogo cuando `course.is_free`, y `CourseViewer` muestra el botón "Inscribirme gratis" (que llama `enrollFree(course.id)` y refresca el curso con `getCourseDetail`) para cursos gratuitos no inscritos, pide login si no hay sesión y mantiene el botón de compra para cursos de pago.

**Estado actual verificado en código:** `lib/api.ts` NO tiene `enrollFree` (se añade en esta spec). `getCourseDetail(courseId)` YA existe y devuelve `CourseDetail` con `enrolled` a nivel de curso (campo de `CourseSummary`) y `has_access` a nivel de lección (`LessonSummary.has_access`); no existe `has_access` a nivel de curso en `schemas.py`/`courses.py` — la UI usa `course.enrolled` para decidir el acceso.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R7 | `CourseViewer` muestra "Inscribirme gratis" para cursos gratuitos no inscritos | Alta |
| R8 | Si el usuario no está autenticado y hace clic en "Inscribirme gratis", se pide login (patrón existente de compra) | Alta |
| R9 | Tras inscribirse, el curso se refresca con `enrolled=true` y se desbloquean las lecciones | Alta |

## 3. Diseño

**Frontend (5.3, components/academy/academy-page.tsx, course-viewer.tsx):**
- **`AcademyPage`:** al recibir el catálogo, cada tarjeta muestra "Gratis" si `course.is_free` (además del precio si es de pago).
- **`CourseViewer`:** en el panel de compra:
  - Si `course.is_free && !course.enrolled && isAuthed` → botón **"Inscribirme gratis"** → llama `enrollFree(course.id)` (nueva función en `lib/api.ts`) → al éxito, refresca el curso (`getCourseDetail(course.id)`, función existente en `lib/api.ts`) para que `enrolled=true` y las lecciones se desbloqueen.
  - Si `course.is_free && !course.enrolled && !isAuthed` → clic en "Inscribirme gratis" → `onRequireLogin` (mismo patrón que el botón de compra).
  - Si `course.enrolled` → no se muestra panel de compra (comportamiento existente).
  - Si `!course.is_free` → botón de compra actual (sin cambios).
- **`lib/api.ts`:** añadir `enrollFree(courseId): Promise<void>` (requiere JWT) — hoy NO existe (verificado). `getCourseDetail(courseId)` ya existe y devuelve `enrolled` (curso) y `has_access` (lección).

## 4. Especificación funcional (SDD)

- **Entrada:** `course` (con `is_free`, `enrolled`), `isAuthed`, callbacks existentes.
- **Salida:** panel de compra con botón correcto según estado.
- **Reglas:**
  - `is_free && !enrolled && isAuthed` → botón "Inscribirme gratis" (llama `enrollFree`); durante la petición el botón se deshabilita (anti doble clic).
  - `is_free && !enrolled && !isAuthed` → clic en "Inscribirme gratis" → `onRequireLogin` (patrón existente de compra, R8); `enrollFree` no se invoca.
  - `enrolled` → sin panel de compra (comportamiento existente).
  - `!is_free` → botón de compra actual (sin cambios).
  - Tras 201/200 de `enrollFree` → refrescar el curso con `getCourseDetail(course.id)` para que `enrolled=true` y las lecciones se desbloqueen (R9).
  - Error de `enrollFree` (red, 400 o 404) → mensaje de error visible sin cerrar el panel.
- **Casos borde:** error de red en `enrollFree` → mensaje de error sin cerrar el panel; doble clic → deshabilitar botón durante la llamada; refresco del curso falla tras inscribirse → mostrar error y permitir reintento; `enrollFree` responde 400 (curso no gratuito) o 404 (curso inexistente) → mostrar el `detail` del backend.

## 5. Criterios de aceptación

- [ ] `CourseViewer` muestra "Inscribirme gratis" solo para cursos gratuitos no inscritos; pide login si no hay sesión.
- [ ] Durante la petición de inscripción el botón se deshabilita (anti doble clic).
- [ ] Tras inscribirse (201/200), el curso se refresca con `enrolled=true` y las lecciones quedan accesibles.
- [ ] Un error de `enrollFree` (red, 400 o 404) se muestra sin cerrar el panel.

## 6. Casos de prueba (TDD Vanilla)

- `test_course_viewer_shows_enroll_free_button_when_free_and_not_enrolled`: Arrange: `course.is_free=true`, `enrolled=false`, `isAuthed=true`. Act: render. Assert: botón "Inscribirme gratis" presente, sin botón de compra.
- `test_course_viewer_enroll_free_requires_login_when_unauthenticated`: Arrange: `is_free=true`, `enrolled=false`, `isAuthed=false`. Act: clic en "Inscribirme gratis". Assert: `onRequireLogin` invocado, `enrollFree` no invocado.
- `test_course_viewer_hides_purchase_panel_when_enrolled`: Arrange: `enrolled=true` (curso gratuito). Act: render. Assert: sin panel de compra ni botón de inscripción.
- `test_course_viewer_refreshes_course_after_enroll_free_success`: Arrange: mock de `enrollFree` resolviendo. Act: clic en "Inscribirme gratis". Assert: `getCourseDetail` (función existente en `lib/api.ts`) invocado para refrescar y el curso pasa a `enrolled=true`.
- `test_course_viewer_shows_error_when_enroll_free_fails`: Arrange: mock de `enrollFree` rechazando. Act: clic. Assert: mensaje de error visible, panel sigue abierto.
- `test_course_viewer_disables_enroll_button_while_loading`: Arrange: mock de `enrollFree` con promesa pendiente. Act: clic y doble clic. Assert: botón deshabilitado, `enrollFree` invocado una sola vez.
- `test_course_viewer_shows_error_message_for_400_404_from_enroll_free`: Arrange: mock de `enrollFree` rechazando con `Error("Este curso no es gratuito")` (400) y luego con `Error("Curso no encontrado")` (404). Act: clic en "Inscribirme gratis". Assert: el mensaje del backend es visible y el panel sigue abierto.
- `test_course_viewer_shows_enroll_free_button_for_unauthenticated_user`: Arrange: `is_free=true`, `enrolled=false`, `isAuthed=false`. Act: render. Assert: el botón "Inscribirme gratis" está presente (el clic pide login, ver test anterior).

## 7. Riesgos y consideraciones

- **UI engañosa:** evitar mostrar "Gratis" y botón de compra a la vez; el estado `is_free` debe ser consistente entre catálogo y detalle (misma fuente: backend).
