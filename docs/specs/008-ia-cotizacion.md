# 008 - Cotización automatizada por IA (Fase 4)

- **Estado:** borrador
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

Implementa la **Fase 4** del roadmap definido en la spec 001: la cotización automatizada por IA para las 4 secciones cotizables (Optimización Comercial y Analítica, Arquitectura e Infraestructura Cloud, Ciberseguridad Avanzada y Cumplimiento, Soporte de Cómputo e Infraestructura Física).

La spec 002 dejó el diseño desacoplado: la generación de cotización vive detrás de la interfaz `QuoteService` con una implementación `ManualQuoteService`. Esta spec define e implementa `AIQuoteService` con **la misma interfaz**, de modo que el sistema migra de manual a automatizado **sin cambios estructurales en endpoints ni modelo de datos**.

La IA pregunta lo necesario (relacionado con la sección), recolecta las respuestas en `QuoteParams` (JSON versionado, ya definido en 002), genera la cotización basada en lo recolectado y en los **parámetros de cotización asignados en la base de datos** por servicio, y **deriva a un agente humano** cuando se requiere (casos complejos, dudas, o baja confianza de la IA).

**Prerrequisito:** la Fase 2 (spec 002) debe estar operando y acumulando cotizaciones manuales reales para calibrar y evaluar la calidad de la IA antes de habilitarla en producción.

## 2. Objetivos

- Implementar `AIQuoteService` cumpliendo la interfaz `QuoteService` definida en 002 (misma firma `generate(lead, params) -> Quote`).
- Definir el **diálogo de IA por sección**: preguntas dinámicas relacionadas con la sección cotizable, configuradas en BD.
- Generar la cotización a partir de las respuestas recolectadas y los **parámetros de cotización por servicio** almacenados en BD.
- Derivar a **agente humano** cuando la IA lo requiera (reglas de negocio configurables).
- Proveer los endpoints de conversación que el `LeadProvider`/landing consumirá para el diálogo.
- Definir el **proveedor de IA configurable** (variable de entorno) sin acoplar el código a un vendor.
- Definir la **evaluación de calidad** de cotizaciones IA vs manuales antes de habilitar en producción.

## 3. Alcance

### Incluye
- `AIQuoteService` (implementación de `QuoteService`).
- Modelo de preguntas de diálogo por sección (`QuoteQuestion`) y respuestas en `QuoteParams`.
- Parámetros de cotización por servicio en BD (extiende el modelo `QuoteParams` de 002 con reglas de precio/descuento).
- Reglas de derivación a agente humano.
- Endpoints de conversación: `POST /leads/{lead_id}/chat` y `GET /leads/{lead_id}/chat/questions`.
- Proveedor de IA configurable vía variables de entorno.
- Evaluación de calidad (comparación contra cotizaciones manuales históricas).
- Especificación SDD + casos TDD Vanilla.

### Excluye
- Entrenamiento o fine-tuning de modelos propios (se usa un proveedor de IA externo vía API).
- Envío automático de la cotización por email al cliente (iteración posterior).
- Integración con CRM externo.
- Automatización del cierre de leads (el cierre sigue siendo manual por el agente).
- Soporte de IA para Labs o Academy (solo las 4 secciones cotizables B2B).

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | `AIQuoteService` implementa la interfaz `QuoteService` (`generate(lead, params) -> Quote`) sin cambios en endpoints | Alta |
| R2 | Las preguntas del diálogo por sección se almacenan en BD (`quote_questions`) y son editables por admin | Alta |
| R3 | `GET /leads/{lead_id}/chat/questions` devuelve la siguiente pregunta (o el set completo) según la sección del lead | Alta |
| R4 | `POST /leads/{lead_id}/chat` recibe la respuesta del usuario, la acumula en `QuoteParams` y devuelve la siguiente pregunta, la cotización, o la derivación a humano | Alta |
| R5 | La generación de cotización usa los parámetros de BD por servicio (precios base, unidades, descuentos, vigencia) | Alta |
| R6 | Reglas de derivación a humano configurables (p. ej. confianza baja, requisitos fuera de catálogo, monto estimado alto, N respuestas ambiguas) | Alta |
| R7 | El proveedor de IA es configurable por variable de entorno (`AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`) | Media |
| R8 | El diálogo y la cotización quedan registrados (auditoría) en `QuoteParams` con `version` incrementada | Media |
| R9 | Evaluación de calidad: comparar cotizaciones IA vs manuales históricas (métrica de desviación) antes de habilitar en producción | Media |
| R10 | El `LeadProvider` (landing) puede iniciar el diálogo de IA tras crear el lead (modo conversacional) | Media |
| R11 | Si la IA deriva a humano, el lead pasa a `en_revision` con `assigned_agent_id` asignable y el flujo manual de 002 continúa | Alta |
| R12 | `AI_PROVIDER` desactivado (vacío) → el sistema se comporta exactamente como la Fase 2 (manual), sin regresión | Alta |

## 5. Diseño / Arquitectura

### 5.1 `AIQuoteService` (backend/services/quote_service.py)

```python
# backend/services/quote_service.py (extiende lo definido en 002)
class QuoteService(Protocol):
    def generate(self, lead: Lead, params: QuoteParams) -> Quote: ...

class ManualQuoteService:
    """Fase 2: el agente humano define monto/vigencia vía POST /admin/leads/{id}/quote."""
    def generate(self, lead, params) -> Quote: ...

class AIQuoteService:
    """Fase 4: la IA recolecta lo necesario por sección (diálogo), genera la
    cotización con parámetros de BD y deriva a agente humano si se requiere."""
    def __init__(self, provider: AIProvider, params_repo: QuoteParamsRepo): ...
    def generate(self, lead, params) -> Quote: ...
    def next_question(self, lead, params) -> Question | None: ...
    def should_escalate(self, lead, params) -> EscalationReason | None: ...
```

- El endpoint `POST /admin/leads/{id}/quote` (002) sigue delegando en la interfaz `QuoteService`; la implementación activa se selecciona por configuración (`QUOTE_SERVICE=manual|ai`), no por código.
- `AIQuoteService` usa un `AIProvider` (abstracción) para no acoplarse a un vendor.

### 5.2 Abstracción de proveedor de IA (backend/services/ai_provider.py)

```python
class AIProvider(Protocol):
    def complete(self, system: str, messages: list[dict]) -> str: ...
    def confidence(self, response: str) -> float: ...  # 0.0 - 1.0

class RouteLLMProvider:
    """Proveedor OpenAI-compatible (p. ej. RouteLLM de Abacus.AI) configurable
    por variables de entorno. No se asume credenciales locales."""
    def __init__(self, base_url: str, api_key: str, model: str): ...
```

- Variables de entorno (backend/.env):
  - `AI_PROVIDER` — vacío (default) = desactivado (comportamiento manual de 002); `routellm` = activado.
  - `AI_BASE_URL` — URL del endpoint OpenAI-compatible (p. ej. RouteLLM).
  - `AI_API_KEY` — clave de API del proveedor (nunca hardcodeada).
  - `AI_MODEL` — modelo a usar.
  - `QUOTE_SERVICE` — `manual` (default) | `ai`; si `ai` sin `AI_PROVIDER` → error de arranque claro.
- El código nunca contiene claves; solo nombres de variables de entorno.

### 5.3 Modelo de datos (backend/services/persistence.py)

**Tabla `quote_questions`** (preguntas del diálogo por sección)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `service_category` | str | Una de las 4 categorías cotizables |
| `question_key` | str | Identificador estable (p. ej. `num_usuarios`, `sla`, `nube_publica`) |
| `question_text` | str | Texto mostrado al usuario |
| `input_type` | str | `text`, `number`, `select`, `boolean` |
| `options` | JSON | Opciones para `select` (nullable) |
| `required` | bool | Si la respuesta es obligatoria |
| `order` | int | Orden en el diálogo |
| `is_active` | bool | Para desactivar preguntas sin borrarlas |

**Tabla `quote_params`** (extiende la de 002)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | (ya existe en 002) |
| `lead_id` | int FK leads.id | |
| `service_category` | str | |
| `params` | JSON | Respuestas del diálogo + metadatos de auditoría (`{answers: {...}, ai_confidence: 0.0, escalated: bool, provider: "routellm", model: "..."}`) |
| `version` | int | Se incrementa en cada actualización del diálogo |
| `created_at` | datetime | |

**Tabla `quote_pricing_rules`** (parámetros de cotización por servicio en BD)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `service_category` | str | Una de las 4 categorías |
| `rule_key` | str | p. ej. `base_price_cents`, `price_per_user_cents`, `discount_pct`, `min_contract_months` |
| `value` | JSON | Valor de la regla |
| `is_active` | bool | |
| `updated_at` | datetime | |

- La IA lee estas reglas para calcular la cotización; un admin las edita (spec 005 extiende el dashboard con esta tabla).

### 5.4 Flujo de diálogo y cotización

```
Lead creado (POST /leads, 002) ──► estado: recibido
        │
        ▼
GET /leads/{id}/chat/questions ──► primera pregunta (según service_category)
        │
        ▼
POST /leads/{id}/chat {answer} ──► acumula en QuoteParams.params.answers
        │
        ├── ¿hay más preguntas? ──► sí → devuelve siguiente pregunta
        │
        └── no → AIQuoteService.generate(lead, params)
                    │
                    ├── should_escalate() == None ──► Quote creada, lead → cotizado
                    │
                    └── should_escalate() == razón ──► lead → en_revision,
                                                       requiere agente humano (002)
```

- El diálogo es **stateful por lead**: el estado vive en `QuoteParams` (respuestas acumuladas), no en memoria del servidor; un lead puede retomar el diálogo desde cualquier dispositivo.
- Si el lead ya tiene cotización (estado `cotizado`), el diálogo no se reabre (o se reabre solo como re-cotización explícita).

### 5.5 Endpoints REST

**Públicos (sin autenticación, asociados al lead por su id):**

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/leads/{lead_id}/chat/questions` | Devuelve la siguiente pregunta pendiente (o `{done: true}` si el diálogo terminó). 404 si el lead no existe; 409 si el lead ya está `cotizado`/`cerrado` |
| POST | `/leads/{lead_id}/chat` | Body: `{question_key, answer}`. Acumula la respuesta, devuelve `{next_question?, quote?, escalated?}`. 422 si la pregunta no corresponde a la sección o la respuesta no cumple el `input_type` |

**Administración (JWT + `is_admin`):**

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/quote-questions` | Lista preguntas por categoría (para edición en 005) |
| POST | `/admin/quote-questions` | Crea pregunta |
| PATCH | `/admin/quote-questions/{id}` | Actualiza pregunta (texto, opciones, orden, activa) |
| GET | `/admin/quote-pricing-rules` | Lista reglas de cotización por servicio |
| PATCH | `/admin/quote-pricing-rules/{id}` | Actualiza regla (precio base, descuento, etc.) |
| POST | `/admin/leads/{lead_id}/evaluate` | Ejecuta la evaluación de calidad de la cotización IA vs manual (ver 5.6) |

### 5.6 Evaluación de calidad (antes de habilitar en producción)

- **Método:** comparar cotizaciones generadas por IA contra cotizaciones manuales históricas de la misma `service_category` y parámetros similares.
- **Métrica:** desviación porcentual media del monto (`abs(ia - manual) / manual * 100`).
- **Umbral de habilitación:** desviación media ≤ 15% en una muestra de ≥ 20 cotizaciones por categoría (configurable).
- **Salida:** reporte `{category, sample_size, mean_deviation_pct, threshold, passed}`.
- La habilitación en producción se hace por variable de entorno (`QUOTE_SERVICE=ai`), no por código.

### 5.7 Integración con el LeadProvider (frontend)

- Tras `POST /leads` exitoso (002), si `QUOTE_SERVICE=ai` y el lead no está `cotizado`, el panel ofrece "Continuar con el diagnóstico" → inicia el diálogo con `GET /leads/{id}/chat/questions` y `POST /leads/{id}/chat`.
- Estados de UI: `form → sending → done` (lead creado) → `chat` (diálogo) → `quote` (cotización mostrada) / `escalated` (mensaje "Un especialista te contactará").
- Si `QUOTE_SERVICE=manual` (default), el panel se comporta exactamente como 002 (sin diálogo).

## 6. Criterios de aceptación

- [ ] `AIQuoteService` implementa `QuoteService` y el endpoint de cotización (002) funciona igual con `QUOTE_SERVICE=manual` y `QUOTE_SERVICE=ai`.
- [ ] Con `AI_PROVIDER` vacío, el sistema se comporta idéntico a la Fase 2 (sin regresión).
- [ ] `GET /leads/{id}/chat/questions` y `POST /leads/{id}/chat` funcionan para las 4 categorías y persisten respuestas en `QuoteParams` con `version` incrementada.
- [ ] La cotización IA usa las reglas de `quote_pricing_rules` de BD (no valores hardcodeados en el prompt).
- [ ] La derivación a humano mueve el lead a `en_revision` y el flujo manual de 002 continúa sin cambios.
- [ ] Las preguntas y reglas son editables por admin (endpoints de 5.5) y visibles en el dashboard (005).
- [ ] La evaluación de calidad produce el reporte de desviación y bloquea `QUOTE_SERVICE=ai` si no se supera el umbral.
- [ ] No hay claves de API en el código; solo variables de entorno.

## 7. Riesgos y consideraciones

- **Calidad de la IA:** la cotización automatizada puede equivocarse. La evaluación de calidad (5.6) y la derivación a humano son obligatorias antes de habilitar en producción; la habilitación es por variable de entorno, reversible en segundos.
- **Alucinaciones / parámetros fuera de catálogo:** el prompt debe restringirse a las reglas de BD; si la IA propone algo fuera de catálogo, `should_escalate()` debe devolver la razón y derivar a humano.
- **Costo por llamada:** el diálogo por lead genera varias llamadas al proveedor; considerar límite de preguntas por lead y timeout.
- **Privacidad:** las respuestas del diálogo pueden contener PII; se almacenan en `QuoteParams` (misma política de retención que 002).
- **Dependencia del proveedor:** si `AI_PROVIDER` falla (timeout, 5xx), el diálogo debe degradar a "derivar a humano" o a "guardar respuestas y continuar manual", nunca perder las respuestas ya recolectadas.
- **Versionado:** `QuoteParams.version` protege cotizaciones históricas cuando cambian las preguntas o reglas.
- **Dependencia con 005:** la edición de preguntas/reglas desde el dashboard se construye en 005; esta spec define la API.

## 8. Especificación funcional (SDD)

### 8.1 `GET /leads/{lead_id}/chat/questions` (público)

- **Entrada:** `lead_id` en ruta.
- **Salida:** `{question: {question_key, question_text, input_type, options?, required}, progress: {answered, total}}` o `{done: true}`.
- **Reglas de negocio:**
  - El lead debe existir → 404 si no.
  - El lead debe estar en `recibido` o `en_revision` (diálogo activo) → 409 si `cotizado`/`cerrado`.
  - Las preguntas se toman de `quote_questions` activas de la `service_category` del lead, ordenadas por `order`.
  - La siguiente pregunta es la primera sin respuesta en `QuoteParams.params.answers`.
- **Casos borde:** lead sin `QuoteParams` (diálogo nunca iniciado) → primera pregunta; todas respondidas → `{done: true}`; categoría sin preguntas configuradas → `{done: true}` (la IA genera con reglas por defecto o deriva a humano); lead con `service_category` `labs` o `academy` (consulta general, spec 002) → el diálogo de IA no aplica: `{done: true}` y el lead sigue el flujo manual (estas categorías no tienen `quote_questions` ni `quote_pricing_rules`, su cotización es siempre humana).

### 8.2 `POST /leads/{lead_id}/chat` (público)

- **Entrada:** `{question_key, answer}`.
- **Salida:** `{next_question?}`, o `{quote: {...}}`, o `{escalated: true, reason}`.
- **Reglas de negocio:**
  - `question_key` debe pertenecer a la sección del lead → 422 si no.
  - La respuesta debe cumplir el `input_type` (número ≥ 0, opción válida para `select`, booleano) → 422.
  - Se acumula en `QuoteParams.params.answers` y se incrementa `version`.
  - Si quedan preguntas → devuelve la siguiente.
  - Si no quedan → `AIQuoteService.generate(lead, params)`:
    - Si `should_escalate()` → lead a `en_revision`, respuesta `{escalated: true, reason}`.
    - Si no → crea `Quote` (monto calculado con `quote_pricing_rules`), lead a `cotizado`, respuesta `{quote}`.
- **Casos borde:** lead inexistente → 404; lead `cotizado`/`cerrado` → 409; proveedor de IA caído → guarda respuestas, lead a `en_revision` con razón `ai_unavailable`, respuesta `{escalated: true, reason: "ai_unavailable"}`; respuesta duplicada a la misma `question_key` → sobrescribe (no duplica).

### 8.3 `AIQuoteService.generate(lead, params) -> Quote`

- **Entrada:** lead + `QuoteParams` con respuestas.
- **Salida:** `Quote` (amount_cents, currency, valid_until, notes) o escalación.
- **Reglas de negocio:**
  - Lee `quote_pricing_rules` de la categoría (precio base, precio por unidad, descuentos, vigencia mínima).
  - Calcula el monto aplicando las reglas a las respuestas (p. ej. `base + price_per_user * num_usuarios`, con `discount_pct` si aplica).
  - `valid_until` = hoy + vigencia de reglas (default 30 días).
  - `should_escalate()` devuelve razón si: confianza del proveedor < umbral, respuesta fuera de catálogo, monto estimado > umbral configurado, o el proveedor falló.
- **Casos borde:** categoría sin reglas → escalar a humano (no inventar precios); respuestas incompletas (preguntas requeridas sin responder) → escalar; monto calculado ≤ 0 → escalar.

### 8.4 `should_escalate(lead, params) -> EscalationReason | None`

- **Entrada:** lead + params.
- **Salida:** `None` (generar cotización) o `{reason: str, detail: str}`.
- **Reglas:** umbrales configurables en `quote_pricing_rules` (`escalation_confidence_threshold`, `escalation_max_amount_cents`); razones: `low_confidence`, `out_of_catalog`, `amount_above_threshold`, `ai_unavailable`, `missing_required_answers`.
- **Casos borde:** múltiples razones simultáneas → se reporta la primera por prioridad (`ai_unavailable` > `missing_required_answers` > `out_of_catalog` > `low_confidence` > `amount_above_threshold`).

### 8.5 Evaluación de calidad (`POST /admin/leads/{lead_id}/evaluate`)

- **Entrada:** `lead_id` (o rango de fechas para evaluación global).
- **Salida:** `{category, sample_size, mean_deviation_pct, threshold, passed}`.
- **Reglas:** compara cotizaciones IA vs manuales de la misma categoría; `passed = sample_size >= min_sample AND mean_deviation_pct <= threshold`; si no `passed`, `QUOTE_SERVICE=ai` no debe habilitarse.
- **Casos borde:** sin cotizaciones manuales suficientes → `passed=false` con `sample_size` insuficiente; categoría sin datos → reporte vacío.

### 8.6 `LeadProvider` (frontend, modo conversacional)

- **Entrada:** lead creado con éxito y `QUOTE_SERVICE=ai`.
- **Salida:** flujo `chat → quote | escalated`.
- **Reglas:** tras `POST /leads` exitoso, si el backend responde `chat_available: true`, el panel muestra "Continuar con el diagnóstico"; cada respuesta se envía a `POST /leads/{id}/chat`; al recibir `quote`, muestra monto/vigencia; al recibir `escalated`, muestra mensaje de contacto.
- **Casos borde:** backend sin IA (`chat_available: false`) → se muestra el estado `done` de 002 sin diálogo; error de red durante el diálogo → reintento sin perder respuestas (se re-sincroniza con `GET /leads/{id}/chat/questions`).

## 9. Casos de prueba (TDD Vanilla)

- `test_ai_quote_service_implements_quote_service_interface`: Arrange: instancia de `AIQuoteService`. Act: verificar firma `generate(lead, params)`. Assert: cumple el `Protocol` `QuoteService` (mismo contrato que `ManualQuoteService`).
- `test_quote_service_switches_by_config_without_code_change`: Arrange: `QUOTE_SERVICE=manual` y `QUOTE_SERVICE=ai` (mock de `AIQuoteService`). Act: invocar `POST /admin/leads/{id}/quote`. Assert: delega en la implementación activa según configuración; el endpoint no cambia.
- `test_ai_disabled_behaves_exactly_as_manual`: Arrange: `AI_PROVIDER` vacío, `QUOTE_SERVICE=manual`. Act: flujo completo de 002 (crear lead, cotizar manual). Assert: idéntico a Fase 2, sin llamadas a proveedor de IA.
- `test_get_questions_returns_first_unanswered`: Arrange: lead `recibido` de `ciberseguridad` con 3 preguntas activas, 1 respondida. Act: `GET /leads/{id}/chat/questions`. Assert: devuelve la pregunta 2 (orden `order`).
- `test_get_questions_404_for_unknown_lead`: Arrange: `lead_id` inexistente. Act: `GET /leads/{id}/chat/questions`. Assert: 404.
- `test_get_questions_409_when_lead_cotizado`: Arrange: lead en estado `cotizado`. Act: `GET /leads/{id}/chat/questions`. Assert: 409.
- `test_get_questions_done_when_all_answered`: Arrange: todas las preguntas respondidas. Act: `GET /leads/{id}/chat/questions`. Assert: `{done: true}`.
- `test_post_chat_accumulates_answer_and_increments_version`: Arrange: lead con `QuoteParams` version 1. Act: `POST /leads/{id}/chat` con respuesta válida. Assert: `params.answers` contiene la respuesta y `version == 2`.
- `test_post_chat_rejects_question_from_other_category`: Arrange: lead de `arquitectura-cloud`. Act: `POST /leads/{id}/chat` con `question_key` de `ciberseguridad`. Assert: 422.
- `test_post_chat_rejects_invalid_answer_type`: Arrange: pregunta `input_type=number`. Act: enviar `answer="abc"`. Assert: 422.
- `test_post_chat_returns_quote_when_dialog_complete`: Arrange: todas las respuestas válidas, reglas de BD configuradas, mock de proveedor con confianza alta. Act: última respuesta. Assert: respuesta `{quote}` con `amount_cents` calculado según reglas y lead en `cotizado`.
- `test_post_chat_escalates_when_low_confidence`: Arrange: mock de proveedor con confianza 0.3 (< umbral). Act: última respuesta. Assert: `{escalated: true, reason: "low_confidence"}`, lead en `en_revision`.
- `test_post_chat_escalates_when_ai_unavailable`: Arrange: mock de proveedor lanzando timeout. Act: última respuesta. Assert: `{escalated: true, reason: "ai_unavailable"}`, respuestas guardadas, lead en `en_revision`.
- `test_post_chat_escalates_when_category_has_no_pricing_rules`: Arrange: categoría sin reglas en `quote_pricing_rules`. Act: diálogo completo. Assert: escalado (no inventa precios).
- `test_generate_uses_pricing_rules_from_db`: Arrange: regla `base_price_cents=50000`, `price_per_user_cents=2000`, respuesta `num_usuarios=10`. Act: `generate`. Assert: `amount_cents == 70000` (50000 + 2000*10).
- `test_generate_applies_discount_pct`: Arrange: regla `discount_pct=10`, monto base 100000. Act: `generate`. Assert: `amount_cents == 90000`.
- `test_should_escalate_priority_order`: Arrange: lead con confianza baja Y monto sobre umbral. Act: `should_escalate`. Assert: razón `low_confidence` (prioridad sobre `amount_above_threshold`).
- `test_evaluate_quality_passes_within_threshold`: Arrange: 20 cotizaciones manuales y 20 IA con desviación media 8%. Act: `POST /admin/leads/{id}/evaluate` (o evaluación global). Assert: `passed=true`, `mean_deviation_pct=8`.
- `test_evaluate_quality_fails_with_insufficient_sample`: Arrange: 3 cotizaciones manuales. Act: evaluación. Assert: `passed=false`, `sample_size < min_sample`.
- `test_lead_provider_starts_chat_when_chat_available`: Arrange: mock de `createLead` resolviendo `{id: 1, chat_available: true}`. Act: enviar formulario. Assert: la UI ofrece "Continuar con el diagnóstico" y al aceptar llama `GET /leads/1/chat/questions`.
- `test_lead_provider_skips_chat_when_not_available`: Arrange: mock de `createLead` resolviendo `{id: 1, chat_available: false}`. Act: enviar. Assert: estado `done` de 002, sin diálogo.
- `test_lead_provider_resyncs_dialog_after_network_error`: Arrange: `POST /leads/{id}/chat` falla por red. Act: reintentar. Assert: se re-sincroniza con `GET /leads/{id}/chat/questions` y no se pierden respuestas previas.
- `test_no_api_keys_in_code`: Arrange: buscar en `backend/` patrones de clave (sk-, AKIA, etc.). Act: grep. Assert: solo nombres de variables de entorno (`AI_API_KEY`), ningún valor real.
