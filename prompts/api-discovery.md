## api

AMBITO
Workspace ai-labs, raiz del repositorio. Lee y escribe codigo solo en api/.
Git se ejecuta desde la raiz; las pruebas usan cwd api/. No leas ni modifiques
auth/ ni web/. Usa IDs H-API-NN y componente api.

CONTEXTO
API FastAPI de tareas y requerimientos en api/app/main.py. Lee README.md,
RETO.md y docs/GOOD_PRACTICES.md. docs/ENDPOINTS.md no existe: el contrato se
deriva del codigo y se registra en HALLAZGOS.md.

OBJETIVO
Mapear rutas, flujo del token, acceso a SQLite y carga de archivos. Crear
HALLAZGOS.md con una matriz de seguimiento: cada hallazgo de RETO.md presente
en el codigo, con evidencia archivo:linea.

RESTRICCIONES
Discovery: no modificar codigo, no crear docs/ENDPOINTS.md, no ejecutar
ataques ni contactar servicios remotos. No dar por cierto un hallazgo sin
archivo y linea. Sin inventar aprobaciones humanas ni resultados de pruebas.

CRITERIOS DE ACEPTACION
Filas con: id, componente api, hallazgo, tipo, explicacion, evidencia
(archivo:linea), severidad (alta/media/baja) y estado inicial Pendiente, u
"No encontrado" si el hallazgo no aparece en el codigo. Orden de mayor a menor
severidad. IDs sin renumerar.

FORMATO DE RESPUESTA
HALLAZGOS.md con la tabla:
id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado
Conservar filas de otros componentes si el archivo ya existe.
