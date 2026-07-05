# Documentación de despliegue y continuación

Documento para retomar el proyecto: estado del despliegue en Easy Panel, cambios realizados y referencias.

---

## 1. Despliegue en Easy Panel (chat / cuentas)

### Configuración en Easy Panel

- **Proyecto:** chat  
- **Servicio/App:** cuentas  
- **Método de compilación:** Dockerfile (no Nixpacks)

### Variables de entorno en Easy Panel

Definir en el servicio **cuentas** (Variables de entorno):

| Variable       | Uso |
|----------------|-----|
| **DATABASE_URL** | URL de MySQL. Debe usar el driver **mysql+mysqlconnector** (no solo `mysql://`) para evitar el error `No module named 'MySQLdb'`. Ejemplo: `mysql+mysqlconnector://mysql:PASSWORD@chat_bd_cuentas:3306/ventas` o con host externo `mysql+mysqlconnector://mysql:PASSWORD@easypanel.clinicamaicao.com:3308/ventas`. |
| **SECRET_KEY**   | Clave secreta para sesiones y CSRF. Usar una clave larga y aleatoria en producción. |
| **PORT**         | Lo inyecta Easy Panel; el Dockerfile usa `PORT` o 5000 por defecto. No suele hace falta definirla a mano. |

### Base de datos

- **Conexión interna (entre servicios):** `chat_bd_cuentas:3306`  
- **Conexión externa:** host `easypanel.clinicamaicao.com`, puerto `3308`  
- **Base de datos:** `ventas`  
- **Usuario:** `mysql` (contraseña en panel; no guardar en repo).

---

## 2. Archivos creados o modificados

### Dockerfile (raíz del proyecto)

- Imagen: `python:3.11-slim`
- Instala dependencias de sistema para **WeasyPrint** (libpango, cairo, **libgdk-pixbuf-2.0-0** con guión, libffi-dev, shared-mime-info).
- Instala dependencias Python desde `requirements.txt`.
- Comando de inicio: `waitress-serve --host=0.0.0.0 --port=${PORT:-5000} run:app`.

### .dockerignore (raíz)

- Excluye `.git`, `__pycache__`, `venv`, `.env`, `.cursor`, `*.log`, etc., para builds más rápidos y seguros.

### .env (local)

- **SECRET_KEY:** añadida (valor por defecto; en producción usar otra en Easy Panel).
- **DATABASE_URL:** formato local con `mysql+mysqlconnector://`; comentario con formato para producción.
- **TESSERACT_CMD:** ruta a Tesseract en Windows para “Leer carnet con cámara” (OCR en entregas).
- Resto: MAIL_*, WHATSAPP_* sin cambios.

---

## 3. Errores resueltos durante el despliegue

1. **Waiting for service chat_cuentas to start**  
   - Causa: Nixpacks + comando/entorno no adecuados.  
   - Solución: pasar a build por **Dockerfile**.

2. **Package 'libgdk-pixbuf2.0-0' has no installation candidate**  
   - Causa: en Debian Trixie el paquete tiene otro nombre.  
   - Solución: en el Dockerfile usar **libgdk-pixbuf-2.0-0** (con guión).

3. **No module named 'MySQLdb'**  
   - Causa: `DATABASE_URL` con prefijo `mysql://` hace que SQLAlchemy intente usar el driver MySQLdb.  
   - Solución: usar **mysql+mysqlconnector://** en `DATABASE_URL` (el proyecto usa `mysql-connector-python`).

---

## 4. Contexto de la aplicación (resumen)

- **Stack:** Flask, SQLAlchemy, Flask-Login, Waitress, WeasyPrint, mysql-connector-python.
- **Entrada:** `run.py` → `app = create_app()` → objeto `app` servido con Waitress.
- **Config:** `config.py` lee `DATABASE_URL`, `SECRET_KEY`, etc.; limpia comillas con `clean_env_var()`.
- **IVA:** En esta plataforma no se calcula IVA (total = subtotal - descuento); cotizaciones y facturas sin IVA.
- **Tokens:** Rutas con token (view_token para entidades; route_token para path). En `before_request` se aceptan view tokens en path para `/quotes/` y `/invoices/`.

---

## 5. Checklist pre-deploy

Antes de cada despliegue en Easy Panel:

1. `DATABASE_URL` con prefijo **mysql+mysqlconnector://** (no `mysql://`).
2. `SECRET_KEY` única y larga en variables de entorno del servicio.
3. `FLASK_ENV=production` (el Dockerfile ya lo define).
4. Ejecutar `python migrate_database.py` si hubo cambios de esquema.
5. Probar en staging/local: login → cotización → **convertir a factura (POST)** → ver factura → PDF.
6. Confirmar que no se generan archivos `debug-*.log` ni `ocr_capture.json` en el servidor.
7. Verificar endpoint `/health` responde `{"status":"ok"}`.

## 6. Arranque recomendado

| Entorno | Comando |
|---------|---------|
| Desarrollo local | `python start.py` o `python start.py --network` |
| Producción local | `python start.py --production` (puerto 8080) |
| Docker / Easy Panel | `waitress-serve --host=0.0.0.0 --port=${PORT:-5000} run:app` |

Copie `.env.example` a `.env` para desarrollo.

## 7. Próximos pasos posibles

- Confirmar que el servicio **cuentas** en Easy Panel queda en estado “Running” y que la app responde en la URL asignada.
- Probar login, cotizaciones, facturas y generación de PDF.
- Si se usa “Leer carnet con cámara” en el servidor: instalar Tesseract en el contenedor (apt) y, si hace falta, definir `TESSERACT_CMD` en variables de entorno del servicio (ruta Linux, p. ej. `/usr/bin/tesseract`).
- Rotar contraseña de la BD si se llegó a exponer en chats o docs.

---

## 8. Referencias rápidas

- **Repositorio / código:** raíz del proyecto “CUENTAS DE COBRO”.
- **Estado del proyecto (módulos, UI, pendientes):** ver `ESTADO_PROYECTO.md` si existe.
- **Plan de despliegue Easy Panel:** ver `c:\Users\hlaverde\.cursor\plans\` (plan “Deploy Easy Panel Compilación”) si se guardó.
- **Este documento:** `DOC_DEPLOY_Y_CONTINUACION.md` en la raíz del proyecto.

---

*Generado para continuar el trabajo de despliegue y configuración en Easy Panel.*
