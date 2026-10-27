# Control seguro de archivos cargados en requisitos

## Fuente

Hallazgo aprobado para especificación: **H-API-04 — La carga no restringe rutas ni tamaño del archivo**.

- Evidencia: `api/app/main.py:94-96` construye la ruta de destino con el nombre proporcionado por la carga, lee el archivo completo en memoria y lo escribe sin validar ruta, extensión ni tamaño. `api/tests/test_api.py:187-197,508-519` cubre una carga ordinaria y una vacía, pero no esos límites.
- Impacto: una persona autenticada podría intentar escribir fuera del directorio de cargas o sobrescribir archivos accesibles por el proceso; además, una carga grande puede consumir memoria y disco. El resultado depende del sistema de archivos y de los permisos del proceso.

## Contexto actual

`POST /api/requirements` recibe un archivo multipart, utiliza el nombre recibido para formar su ruta dentro del directorio configurado y lee su contenido completo antes de escribirlo. En caso de éxito responde `201` con `owner`, `fileName`, `storedAt` y `size`.

## Problema confirmado

El endpoint no aplica una política verificable para impedir que el nombre de archivo salga del directorio de cargas, ni establece límites de tamaño o extensión. Por ello, no se puede asegurar que las cargas se mantengan dentro del destino previsto ni que su consumo de recursos esté acotado.

## Comportamiento a preservar

- Mantener `POST /api/requirements` y la recepción del archivo mediante el campo multipart `file`.
- Mantener la autenticación requerida y derivar `owner` de la identidad verificada, no de datos proporcionados en la carga.
- Para cargas aceptadas, mantener el estado `201` y las claves y tipos de la respuesta actual: `owner`, `fileName`, `storedAt` y `size`.
- Mantener el comportamiento de las cargas válidas existentes, sujeto a la política de extensión y tamaño que se acuerde.

## Alcance

- Definir y hacer verificables las reglas de nombre y destino para que una carga no pueda escribir fuera del directorio autorizado.
- Aceptar únicamente extensiones `.txt`, `.md` y `.json`, sin distinguir mayúsculas y minúsculas, y limitar cada archivo a 5 MiB.
- Normalizar nombres con rutas a su nombre base y rechazar nombres vacíos o inválidos.
- Rechazar nombres duplicados sin reemplazar archivos existentes.
- Devolver `storedAt` como ubicación relativa, igual al nombre normalizado almacenado.
- Rechazar cargas que incumplan esas reglas sin dejar archivos parciales.
- Añadir criterios de prueba para nombres, extensiones y límites de tamaño.

## Fuera de alcance

- Cambios a JWT, autenticación, autorización de tareas u otros endpoints.
- Cambios al esquema de persistencia de tareas o a la estructura general de capas de la API.
- Cambios al formato de éxito de `POST /api/requirements`, salvo decisión explícita sobre el valor de `storedAt`.
- Almacenamiento externo, antivirus o procesamiento del contenido del archivo.

## Criterios de aceptación

1. Un nombre de archivo que incluya rutas absolutas o segmentos que intenten salir del directorio autorizado no provoca escrituras fuera de ese directorio.
2. Solo se aceptan archivos `.txt`, `.md` y `.json` (comparación sin distinguir mayúsculas y minúsculas); otra extensión se rechaza con `400`.
3. Un archivo de hasta 5 MiB inclusive se acepta; uno mayor se rechaza con `413`.
4. Una carga rechazada no crea ni reemplaza archivos y no deja contenido parcial en el directorio de destino.
5. Se prueba el tamaño límite y el caso que lo excede; el caso excedido se rechaza mientras se lee en bloques, sin acumular el archivo completo en memoria.
6. Una carga válida mantiene el estado `201`, las claves de respuesta y el `owner` de la identidad autenticada; `fileName` es el nombre normalizado, `storedAt` es esa ubicación relativa y `size` representa los bytes almacenados.
7. Las pruebas verifican nombres con separadores de Windows y POSIX, extensiones válidas/no válidas, límites y colisiones.

## Contratos afectados/protegidos

- **Protegido:** `POST /api/requirements`, autenticación requerida, campo multipart `file`, código de éxito `201` y claves/tipos actuales de la respuesta (`owner`, `fileName`, `storedAt`, `size`).
- **Protegido:** `owner` refleja la identidad autenticada y no puede ser elegido por quien carga el archivo.
- **Definido para el error:** `400` para nombre/extensión inválidos, `413` para exceso de tamaño y `409` para nombre duplicado, con el formato de error FastAPI.
- **Definido para `storedAt`:** ubicación relativa igual a `fileName`; no se devuelve una ruta física del servidor.

## Riesgos, supuestos y preguntas abiertas

- Decisiones aprobadas para esta implementación: máximo 5 MiB; extensiones `.txt`, `.md` y `.json`; normalizar a nombre base; rechazar colisiones; permitir archivos vacíos; devolver `storedAt` relativo.
- La validación de extensión no inspecciona el contenido real del archivo; no se incluye análisis de contenido en este alcance.
- La capa multipart puede usar recursos temporales antes de la validación de la ruta; el límite de lectura acota el almacenamiento de la aplicación, pero no sustituye un límite del cuerpo HTTP en la infraestructura.
- La protección del sistema de archivos depende también de los permisos efectivos del proceso y del directorio de cargas configurado.
