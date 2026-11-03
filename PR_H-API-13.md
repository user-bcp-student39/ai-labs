## Cambio

- Issue / hallazgo: H-API-13 (componente api). Sin Issue remoto: en el Día 1 no se crean Issues ni PR; este archivo es el borrador local.
- Rama: `day1/prompting` (commits `94b8a22` código y pruebas, `b02a38b` documentación).
- Comportamiento anterior: `POST /api/tasks` aceptaba cualquier cuerpo y convertía cada campo con `str()`. Admitía título vacío, `status`/`priority` arbitrarios (por ejemplo `"high"`, que no cuenta en `highPriorityOpen`), textos sin tope y `null` guardado como `"None"`.
- Resultado: la API valida la entrada antes de insertar (api/app/task_validation.py, invocado desde api/app/main.py). Si es inválida responde **400** `{"detail":[{"field","message"}]}` con todos los campos erróneos, sin devolver el valor recibido, y no crea la tarea.
- Reglas aprobadas:
  - `title` obligatorio, texto no vacío, máximo 200.
  - `description` texto, máximo 2000 (por defecto `""`).
  - `status` ∈ TODO, IN_PROGRESS, DONE, ARCHIVED (por defecto TODO), solo mayúsculas.
  - `priority` ∈ HIGH, MEDIUM, LOW (por defecto MEDIUM), solo mayúsculas.
- Preservado: 201 y campos de la tarea (`id`, `title`, `description`, `status`, `owner`, `priority`, `createdAt`); defaults; 401 en las cinco rutas; 422 sin cuerpo o con cuerpo no objeto; `GET /api/tasks` y `GET /api/summary` sin cambios; lectura de `owner` del cuerpo intacta (H-API-02, fuera de alcance); SQL parametrizado de repository.py sin tocar.
- Cambio de contrato (aprobado): `{}` o `title` vacío pasan de 201 a 400; valores de `status`/`priority` fuera del conjunto pasan de 201 a 400. Se ajustó la prueba `test_create_with_empty_payload_applies_defaults`, ahora `test_create_with_title_only_applies_defaults`.
- No resuelto / fuera de alcance: H-API-01, 02, 04 a 12 y 14 a 16; migración de filas antiguas con valores fuera del conjunto.

## Comprobación

| Comando (desde la raíz) | Resultado |
|---|---|
| `python tools/lab.py test api` (baseline, antes del cambio) | 44 passed, 5 xfailed; cobertura 100 % |
| `python tools/lab.py test api` (después) | 79 passed, 5 xfailed, 0 fallos; cobertura 100 % (165 sentencias, 30 ramas); umbral 85 % cumplido |

- Los 5 xfail son los mismos de H-API-02 y H-API-04 (strict, siguen fallando como antes).
- 35 pruebas nuevas en api/tests/test_task_validation.py: válidos, cada valor permitido, límites exactos, 17 entradas inválidas parametrizadas sin fila creada, múltiples errores, mensaje sin eco del valor, 422 sin cuerpo, 401 antes de validar, `owner` aún aceptado.
- Verificado en ejecución: cuerpo no objeto (lista) y JSON inválido devuelven 422.
- No ejecutado: ruff/mypy (no instalados en api/.venv); build Docker; CodeQL y Dependency Review (workflows remotos, no hay push); pruebas de web contra el nuevo 400.
- Documentación: [docs/ENDPOINTS.md](../docs/ENDPOINTS.md) (POST /api/tasks, errores comunes, riesgos y preguntas 1 y 2 cerradas), [docs/TESTING.md](../docs/TESTING.md) (ejecución E4) y [HALLAZGOS.md](../HALLAZGOS.md) (H-API-13). Las decisiones de diseño están en la conversación de arquitectura; PLAN.md no se modificó.

Riesgos residuales:
- Si web envía `status`/`priority` en minúsculas o crea tareas sin título, recibirá 400. No se verificó qué envía web (fuera del alcance acordado); confirmar antes de integrar.
- El 400 tiene formato propio (`field`/`message`), distinto del 422 de FastAPI.
- Filas antiguas con valores fuera del conjunto se siguen listando y contando como hasta ahora.

Cómo revertir: `git revert 94b8a22 b02a38b` (o revertir solo 94b8a22 para volver al comportamiento anterior; en ese caso restaurar también la prueba renombrada).

## Revisión humana

Pendiente. La persona revisora registra aquí su decisión y motivos. La salida de un agente no sustituye esta revisión.
