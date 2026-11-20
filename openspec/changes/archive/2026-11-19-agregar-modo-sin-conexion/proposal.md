## Why

La app instalada necesita una respuesta clara cuando pierde internet (#26).

## What Changes

Un service worker público en la raíz del sitio conserva la página sin conexión y una lista de archivos estáticos propios. La navegación vuelve a consultar la red al reintentar.
