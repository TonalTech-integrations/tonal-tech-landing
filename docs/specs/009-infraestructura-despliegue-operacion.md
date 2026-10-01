# 009 - Infraestructura, despliegue y operación

- **Estado:** borrador
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

Las specs 002–008 definen **qué** construir; esta spec define **dónde corre, cómo se despliega y cómo se opera** el sistema completo (frontend estático, backend FastAPI, PostgreSQL, AWS S3, Stripe) en cada ambiente.

Hoy el proyecto solo tiene despliegue automático del frontend estático a GitHub Pages (`.github/workflows/deploy.yml`); el backend no tiene destino de producción definido, los contenedores corren en modo desarrollo, no hay estrategia de secretos por ambiente, ni monitoreo, ni backups, ni procedimiento de rollback. La spec 007 corrige las imágenes y el pipeline (build de producción, tests en CI, imagen del backend); **esta spec es transversal al roadmap**: define los ambientes, la topología de despliegue, la gestión de secretos, el aprovisionamiento de servicios externos, el monitoreo, los respaldos y los runbooks de deploy/rollback/mantenimiento que aplican desde la Fase 1 hasta la Fase 4.

## 2. Objetivos

- Definir los ambientes del proyecto (`dev`, `staging`, `prod`) y su configuración por ambiente.
- Definir la topología de despliegue de producción: frontend (GitHub Pages), backend (VM/servidor con contenedores), base de datos, S3 y Stripe.
- Establecer la gestión de secretos y variables de entorno por ambiente (sin valores en el repositorio).
- Definir el proceso de despliegue (runbook) por ambiente, con aprobación manual para producción.
- Definir monitoreo básico (health checks, logs, alertas) y respaldos de base de datos.
- Definir el procedimiento de rollback por componente.
- Alinear la operación con la fase de Mantenimiento del ciclo iterativo del proyecto.

## 3. Alcance

### Incluye
- Ambientes `dev`, `staging`, `prod` y su matriz de configuración.
- Topología de despliegue (frontend estático, backend en contenedores, PostgreSQL, S3, Stripe).
- Gestión de secretos y variables de entorno por ambiente (solo nombres, nunca valores).
- Aprovisionamiento de PostgreSQL, bucket S3 y configuración de Stripe (test/live, webhook).
- Health checks, logging y alertas básicas.
- Respaldos de base de datos y retención.
- Runbook de despliegue, rollback y mantenimiento periódico.
- Especificación SDD + casos TDD Vanilla (pruebas de infraestructura tipo smoke/config).

### Excluye
- Corrección de Dockerfiles y pipeline CI/CD (cubierto por la spec 007, ítems e, f, g).
- Funcionalidad de negocio (cubierta por specs 002–006 y 008).
- Elección final y costos del proveedor de hosting del backend (se dejan criterios y una opción de referencia).
- Alta disponibilidad multi-región, autoscaling o Kubernetes (fuera de escala actual del proyecto).
- CDN/WAF avanzado (se menciona como opción futura).

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | Existen 3 ambientes definidos (`dev`, `staging`, `prod`) con configuración separada | Alta |
| R2 | Ningún secreto o valor sensible vive en el repositorio; solo nombres de variables | Alta |
| R3 | El frontend de producción se despliega en GitHub Pages (estado actual) con `NEXT_PUBLIC_API_BASE_URL` apuntando al backend de producción | Alta |
| R4 | El backend corre en producción como contenedor (imagen de 007-f) detrás de HTTPS, con `uvicorn` sin `--reload` | Alta |
| R5 | PostgreSQL de producción es una instancia persistente (gestionada o contenedor con volumen) con backups diarios y retención definida | Alta |
| R6 | Stripe opera en modo `test` en dev/staging y `live` en prod, con su webhook registrado por ambiente | Alta |
| R7 | `GET /` del backend sirve como health check monitoreado; caída genera alerta | Media |
| R8 | Logs de backend a stdout con rotación en el host (driver de logs del contenedor) | Media |
| R9 | Runbook de deploy documentado: staging automático tras merge a `main`, producción con aprobación manual | Alta |
| R10 | Rollback documentado y probado por componente (frontend, backend, BD) | Alta |
| R11 | `PAYMENTS_MOCK=true` solo en `dev`; prohibido en `prod` (validación de arranque) | Alta |
| R12 | Tareas de mantenimiento periódico definidas (rotación de secretos, revisión de backups, actualización de dependencias) | Media |

## 5. Diseño / Arquitectura

### 5.1 Ambientes

| Aspecto | dev | staging | prod |
|---------|-----|---------|------|
| Dónde corre | Máquina local (podman-compose) | Mismo servidor que prod, puertos distintos (o namespace separado) | Servidor de producción |
| Frontend | `pnpm dev` (3000) | Build estático servido localmente | GitHub Pages (`/tonal-tech-landing`) |
| Backend | `uvicorn --reload` (8000) | Contenedor imagen release candidata | Contenedor imagen etiquetada |
| Base de datos | SQLite local o Postgres local | PostgreSQL staging | PostgreSQL prod |
| Stripe | `PAYMENTS_MOCK=true` o claves `test` | Claves `test` | Claves `live` |
| `PAYMENTS_MOCK` | `true` permitido | `false` | `false` (obligatorio, validado al arranque) |
| `JWT_SECRET_KEY` | Valor local | Secreto propio | Secreto propio, rotado |
| CORS | `http://localhost:3000` | URL de staging | URL pública de Pages |

### 5.2 Topología de despliegue (producción)

```
USUARIO
   │
   ├── HTTPS ──► GitHub Pages ── frontend estático (out/)
   │                 │
   │                 └── fetch JSON (JWT) ──► https://api.<dominio>  ──► Backend FastAPI
   │                                                                      (contenedor, 007-f)
   │                                                                         │
   │                                              ┌──────────────────────────┼───────────────────┐
   │                                              ▼                          ▼                   ▼
   │                                       PostgreSQL (prod)            AWS S3            Stripe API
   │                                       backups diarios         (bucket videos)      (modo live)
   │                                                                         ▲
   └────────────────────────── Stripe webhook (checkout.session.*) ──────────┘
                              → POST https://api.<dominio>/payments/webhook
```

- **Frontend:** GitHub Pages (ya operativo). La variable `NEXT_PUBLIC_API_BASE_URL` se inyecta en el build del workflow (007-g) vía secret/variable de GitHub Actions.
- **Backend:** una VM/VPS Linux (criterio de referencia: 2 vCPU / 4 GB RAM / SSD, Docker o Podman, proxy HTTPS con Caddy o nginx + certificado Let's Encrypt). Puerto interno 8000, expuesto solo vía proxy en 443.
- **Base de datos:** opción recomendada PostgreSQL gestionado; alternativa aceptada: contenedor PostgreSQL con volumen persistente en la misma VM + backups externos.
- **DNS:** `api.<dominio>` → VM. El subdominio y certificado se documentan en el runbook.

### 5.3 Gestión de secretos

- Un archivo `.env` por ambiente, **fuera del repositorio** (`.gitignore` ya debe cubrirlo; verificar en Fase 1).
- Frontend: variables `NEXT_PUBLIC_*` en GitHub (Actions secrets/variables) — son públicas por diseño en el bundle, nunca contienen secretos.
- Backend (prod): `.env` en la VM con permisos `600`, inyectado por `env_file` en compose; acceso solo por SSH del equipo.
- Rotación: `JWT_SECRET_KEY`, claves Stripe y credenciales AWS se rotan al menos cada 90 días o ante sospecha de exposición (procedimiento en 5.8).
- **Prohibido:** imprimir valores de `.env` en logs, CI o documentación. Las verificaciones usan salida enmascarada (`VAR=<set>`).

### 5.4 Base de datos: aprovisionamiento y respaldos

- `init_db()` (existente) crea tablas y aplica migraciones suaves al arrancar el backend; staging y prod arrancan contra su propia base.
- **Backups prod:** `pg_dump` diario vía cron en la VM (o backup del servicio gestionado), compresión y copia a almacenamiento externo (bucket S3 separado, prefijo `backups/`), retención 30 días.
- **Prueba de restauración:** mensual, en staging, documentada en el runbook (5.8).
- SQLite queda limitado a `dev`; staging y prod usan PostgreSQL vía `DATABASE_URL`.

### 5.5 Stripe por ambiente

- Dev: `PAYMENTS_MOCK=true` (sin llamadas reales) o claves `test`.
- Staging: claves `test` + webhook de prueba registrado (`/payments/webhook`).
- Prod: claves `live` + webhook `live` registrado apuntando a `https://api.<dominio>/payments/webhook`, con su propio `STRIPE_WEBHOOK_SECRET`.
- Eventos mínimos suscritos: `checkout.session.completed`, `checkout.session.expired`, `checkout.session.async_payment_failed`, `charge.refunded` (007-h).

### 5.6 Monitoreo, logs y alertas

- **Health check:** `GET /` del backend (existente) monitoreado cada 5 min (servicio externo de uptime o cron + curl); 2 fallos consecutivos → alerta al canal del equipo.
- **Logs:** backend y proxy a stdout; el runtime de contenedores rota (`--log-opt max-size=10m max-file=3`). Nivel INFO en prod; DEBUG prohibido en prod.
- **Métricas de negocio:** las de acceso las cubre la spec 006; esta spec solo cubre salud de infraestructura.

### 5.7 Runbook de despliegue

1. **Merge a `main`** → CI (007-g): lint + `tsc --noEmit` + pytest + build. Si falla, no se despliega nada.
2. **Frontend:** deploy automático a Pages (flujo actual).
3. **Backend → staging:** build de imagen etiquetada `:main-<sha>`; deploy a staging; smoke tests (5.9 SDD).
4. **Backend → prod:** aprobación manual; pull de la misma imagen ya validada en staging; `compose up -d`; verificar health check y un flujo de humo (login + catálogo).
5. **Post-deploy:** registrar fecha, versión (sha) y responsable en el log de despliegues del proyecto.

### 5.8 Runbook de rollback

- **Frontend:** re-deploy del artefacto anterior en Pages (re-run del workflow del commit previo).
- **Backend:** `compose` apunta a la etiqueta de imagen anterior (`:main-<sha-previo>`) y reinicio; verificar health check.
- **Base de datos:** restaurar último backup en staging primero; solo restaurar en prod con ventana acordada (los enrollments/compras nuevos posteriores al backup se re-sincronizan manualmente desde Stripe si aplica).
- **Secretos comprometidos:** revocar en el proveedor (Stripe/AWS), generar nuevos, actualizar `.env` del ambiente afectado, reiniciar backend, registrar incidente.

### 5.9 Mantenimiento periódico (fase Mantenimiento del ciclo)

| Frecuencia | Tarea |
|------------|-------|
| Semanal | Revisar alertas de uptime y errores en logs |
| Mensual | Prueba de restauración de backup en staging; revisión de dependencias (`pnpm outdated`, `pip list --outdated`) |
| Trimestral | Rotación de secretos; revisión de accesos (quién tiene SSH/Stripe/AWS) |
| Por iteración | Verificar que el pipeline siga verde y que los smoke tests cubran los endpoints nuevos de la iteración |

## 6. Criterios de aceptación

- [ ] Existe configuración separada por ambiente (dev/staging/prod) sin secretos en el repositorio.
- [ ] El backend de producción corre como contenedor detrás de HTTPS en `api.<dominio>`, sin `--reload`.
- [ ] `PAYMENTS_MOCK=false` es obligatorio en prod y el backend falla al arrancar si está en `true` con claves `live`.
- [ ] PostgreSQL de prod tiene backups diarios con retención de 30 días y una restauración de prueba documentada.
- [ ] Stripe tiene webhooks registrados por ambiente (test/live) apuntando a `/payments/webhook`.
- [ ] El health check del backend está monitoreado con alerta tras 2 fallos consecutivos.
- [ ] Los runbooks de deploy y rollback están documentados y el rollback de backend se probó al menos una vez en staging.
- [ ] El deploy a producción requiere aprobación manual y deja registro (fecha, sha, responsable).

## 7. Riesgos y consideraciones

- **Backend sin destino definido hoy:** hasta que exista la VM/servidor, las specs 002–008 solo son operables en local. La contratación del servidor es el desbloqueo de Fase 1 (007) + 009.
- **Punto único de fallo:** una sola VM para backend + BD es aceptable a esta escala, pero el backup externo diario es la pieza que lo hace tolerable; sin backups probados, no hay prod.
- **Export estático:** el frontend no puede leer variables en runtime; cambiar `NEXT_PUBLIC_API_BASE_URL` implica re-build y re-deploy (limitación conocida de `output: "export"`).
- **Costos:** Pages es gratuito; VM, PostgreSQL gestionado, S3 y llamadas de IA (008) son costos recurrentes a presupuestar fuera de esta spec.
- **Secretos en historial:** si alguna vez se comiteó un `.env`, hay que rotar esos valores aunque el archivo ya no esté en el repo (el historial de git los conserva).
- **CORS:** `CORS_ORIGINS` de prod debe listar solo la URL pública de Pages; un `*` en prod invalida la protección.

## 8. Especificación funcional (SDD)

### 8.1 Configuración por ambiente

- **Entrada:** nombre de ambiente (`dev` | `staging` | `prod`) + `.env` del ambiente.
- **Salida:** `Settings` validadas (pydantic) con los valores del ambiente.
- **Reglas de negocio:**
  - En `prod`: `PAYMENTS_MOCK` debe ser `false`, `JWT_SECRET_KEY` debe estar definida por entorno (no default), `CORS_ORIGINS` no puede contener `*`, Stripe debe usar claves `live` (prefijo `sk_live`); violación → el backend no arranca (error claro al inicio).
  - En `dev`: `PAYMENTS_MOCK=true` permitido; SQLite permitido.
- **Casos borde:** variable obligatoria ausente → fallo de arranque con el nombre de la variable faltante; `CORS_ORIGINS` con espacios/extra comas → se normaliza (comportamiento ya existente en `get_cors_origins`).

### 8.2 Deploy de backend (staging/prod)

- **Entrada:** imagen etiquetada `:main-<sha>` publicada por CI (007-g) + aprobación manual (solo prod).
- **Salida:** contenedor nuevo sirviendo en 443 vía proxy; contenedor anterior detenido.
- **Reglas:** prod solo recibe imágenes que pasaron smoke tests en staging; el deploy registra sha/fecha/responsable; health check debe responder 200 en < 60s tras el arranque o se considera deploy fallido.
- **Casos borde:** health check falla tras deploy → rollback automático a la etiqueta anterior (procedimiento 5.8).

### 8.3 Health check y alerta

- **Entrada:** `GET /` cada 5 minutos.
- **Salida:** 200 `{"status": "ok", ...}`; tras 2 fallos consecutivos → alerta.
- **Reglas:** la alerta incluye ambiente, hora y último código de respuesta; al recuperarse, se envía aviso de recuperación.
- **Casos borde:** respuesta 200 pero lenta (> 5s) → cuenta como degradado, se registra pero no alerta hasta 3 ocurrencias.

### 8.4 Backup y restauración de PostgreSQL

- **Entrada:** cron diario (backup) / backup seleccionado (restauración).
- **Salida:** archivo `.dump` comprimido en almacenamiento externo con retención 30 días; restauración verificada en staging.
- **Reglas:** un backup fallido genera alerta igual que una caída del backend; la restauración mensual en staging verifica conteos de tablas críticas (`users`, `courses`, `enrollments`, `purchases`) contra valores esperados.
- **Casos borde:** espacio insuficiente en destino → alerta; backup de 0 bytes o corrupto → alerta inmediata, no cuenta como backup del día.

### 8.5 Rollback

- **Entrada:** componente (frontend | backend | bd) + versión destino.
- **Salida:** componente corriendo en la versión anterior verificada por health check / smoke.
- **Reglas:** rollback de backend nunca cambia la BD (las migraciones de `init_db` son aditivas); rollback de BD solo con ventana acordada y aviso; todo rollback queda registrado.
- **Casos borde:** la imagen anterior ya no existe en el host → se reconstruye desde el sha con CI antes de aplicar rollback.

## 9. Casos de prueba (TDD Vanilla)

- `test_prod_settings_reject_payments_mock_true`: Arrange: `Settings` con ambiente `prod` y `PAYMENTS_MOCK=true`. Act: validar arranque. Assert: error de configuración explícito; la app no levanta.
- `test_prod_settings_reject_wildcard_cors`: Arrange: `CORS_ORIGINS="*"` en prod. Act: validar. Assert: error de arranque.
- `test_prod_settings_reject_default_jwt_secret`: Arrange: prod sin `JWT_SECRET_KEY` de entorno. Act: validar. Assert: error de arranque (coherente con 007-c).
- `test_prod_settings_require_live_stripe_keys`: Arrange: prod con clave `sk_test_...`. Act: validar. Assert: error de arranque indicando que se requieren claves live.
- `test_dev_settings_allow_mock_and_sqlite`: Arrange: ambiente `dev` con `PAYMENTS_MOCK=true` y SQLite. Act: validar. Assert: arranque permitido.
- `test_missing_required_env_var_names_it_in_error`: Arrange: entorno sin `AWS_S3_BUCKET`. Act: instanciar `Settings`. Assert: el error menciona `AWS_S3_BUCKET`.
- `test_health_endpoint_returns_200_after_deploy`: Arrange: backend recién desplegado. Act: `GET /`. Assert: 200 con `status: ok` en menos de 60s desde el arranque.
- `test_health_monitor_alerts_after_two_failures`: Arrange: monitor simulado con endpoint caído. Act: 2 chequeos fallidos consecutivos. Assert: se emite una alerta (una sola, no por cada fallo).
- `test_backup_job_produces_non_empty_dump`: Arrange: cron de backup ejecutado contra staging. Act: inspeccionar el artefacto. Assert: archivo existe, tamaño > 0, y aparece en el destino externo con la fecha del día.
- `test_backup_retention_deletes_older_than_30_days`: Arrange: 35 backups diarios simulados. Act: ejecutar limpieza. Assert: quedan exactamente 30, los más recientes.
- `test_restore_drill_matches_critical_table_counts`: Arrange: restaurar último backup en staging. Act: contar filas de `users`, `courses`, `enrollments`, `purchases`. Assert: conteos iguales a los registrados al momento del backup.
- `test_rollback_backend_restores_previous_image`: Arrange: deploy fallido de `:main-<sha-n>` (health check KO). Act: procedimiento de rollback. Assert: corre `:main-<sha-n-1>` y health check 200.
- `test_rollback_backend_does_not_touch_database`: Arrange: rollback de backend ejecutado. Act: comparar conteos de tablas antes/después. Assert: sin cambios en la BD.
- `test_deploy_to_prod_requires_manual_approval`: Arrange: pipeline en CI con staging verde. Act: inspeccionar el job de prod. Assert: el job de prod es manual (`workflow_dispatch` o environment con reviewers) y no corre automáticamente.
- `test_no_secret_values_in_repo_or_ci_logs`: Arrange: buscar patrones de clave (`sk_live`, `sk_test`, `AKIA`, contraseñas) en el árbol del repo y salida de CI. Act: grep. Assert: solo nombres de variables; ningún valor.
- `test_frontend_build_injects_prod_api_url`: Arrange: variable `NEXT_PUBLIC_API_BASE_URL` de prod en Actions. Act: build del frontend e inspección del bundle generado. Assert: las llamadas de `lib/api.ts` apuntan a `https://api.<dominio>` y no a `localhost`.
