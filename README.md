# Documentación de la Aplicación de Cotizaciones y Facturas

**Para usuarios finales (inicio de sesión, roles, uso de módulos):** ver [MANUAL_USUARIO.md](MANUAL_USUARIO.md).

## 1. Descripción General

Esta es una aplicación web desarrollada con Flask que permite la gestión integral de clientes, productos, cotizaciones y facturas. La aplicación está diseñada para facilitar el proceso de creación de documentos comerciales, su envío por correo electrónico y la conversión de cotizaciones en facturas. Incluye también un sistema de autenticación de usuarios con roles y un módulo básico de gestión de inventario.

## 2. Tecnologías y Dependencias Clave

La aplicación se basa en el ecosistema de Python y Flask. Las dependencias principales se gestionan a través del archivo `requirements.txt`.

*   **Backend:** Python
*   **Framework Web:** Flask
*   **Base de Datos:** SQLAlchemy (ORM) con `mysql-connector-python`, configurado para MySQL.
*   **Autenticación:** Flask-Login
*   **Formularios:** Flask-WTF (con WTForms)
*   **Generación de PDF:** WeasyPrint
*   **Envío de Correos:** Flask-Mail
*   **Variables de Entorno:** `python-dotenv`
*   **Internacionalización:** Flask-Babel

## 3. Estructura del Proyecto

El proyecto sigue una estructura modular utilizando Blueprints de Flask.

```
/
├── app/                  # Directorio principal de la aplicación
│   ├── __init__.py       # Fábrica de la aplicación (create_app)
│   ├── models/           # Modelos de la base de datos (SQLAlchemy)
│   ├── routes/           # Lógica de las rutas (Blueprints)
│   ├── templates/        # Plantillas HTML (Jinja2)
│   ├── forms.py          # Definiciones de formularios (WTForms)
│   └── decorators.py     # Decoradores personalizados (ej. role_required)
├── venv/                 # Entorno virtual de Python
├── config.py             # Clases de configuración
├── start.py              # Script principal para iniciar el servidor (RECOMENDADO)
├── run.py                # Script de inicio simple (modo desarrollo)
├── run_production.py     # Script de inicio para producción
├── requirements.txt       # Lista de dependencias de Python
└── .env                  # Archivo para variables de entorno (no versionado)
```

## 4. Configuración (`config.py`)

La configuración se gestiona en la clase `Config` dentro de `config.py`. Carga variables sensibles (como claves secretas y credenciales de base de datos/email) desde un archivo `.env` para mantener la seguridad.

*   `SECRET_KEY`: Clave para la protección contra CSRF y la gestión de sesiones.
*   `SQLALCHEMY_DATABASE_URI`: Cadena de conexión a la base de datos.
*   `MAIL_*`: Configuración para el servidor SMTP para el envío de correos.
*   `WHATSAPP_*`: Configuración para la integración con la API de WhatsApp Business.

## 5. Modelos de Datos (`app/models/__init__.py`)

Define la estructura de la base de datos utilizando SQLAlchemy ORM.

*   **User:** Almacena la información de los usuarios (`username`, `name`, `email`, `password_hash`, `role`). El rol puede ser 'user' o 'admin'.
*   **Client:** Guarda los datos de los clientes (`name`, `document_number`, `contact_person`, `email`, `whatsapp_number`, etc.).
*   **Product:** Contiene la información de los productos (`code`, `name`, `description`, `price`, `stock`).
*   **Quote:** Representa una cotización (`quote_number`, `date`, `client_id`, `total_amount`).
*   **QuoteItem:** Representa un ítem dentro de una cotización, vinculando `Quote` y `Product`.
*   **Invoice:** Representa una factura (`invoice_number`, `date`, `due_date`, `payment_date`, `client_id`, `total_amount`).
*   **InvoiceItem:** Representa un ítem dentro de una factura, vinculando `Invoice` y `Product`.
*   **Payment:** Almacena la información de los pagos recibidos por una factura.

## 6. Formularios (`app/forms.py`)

Utiliza `Flask-WTF` para crear, validar y procesar formularios web.

*   **LoginForm / RegistrationForm:** Para inicio de sesión y registro de usuarios (el registro incluye el campo `name`).
*   **ClientForm / ProductForm:** Para crear y editar clientes y productos.
*   **QuoteForm / QuoteItemForm:** Para crear la cabecera de una cotización y para añadirle ítems.
*   **InvoiceForm / InvoiceItemForm:** Para crear la cabecera de una factura y para añadirle ítems.
*   **InventoryForm:** Para actualizar el stock de un producto.
*   **AdminEditUserForm:** Para que los administradores editen la información de otros usuarios.
*   **UpdateQuoteStatusForm:** Para cambiar el estado de una cotización.
*   **InvoiceFinancialUpdateForm:** Para actualizar el estado financiero de una factura y registrar pagos.

## 7. Rutas y Lógica de Negocio (`app/routes/`)

La lógica de la aplicación está organizada en Blueprints.

*   **main.py:**
    *   `/`, `/index`: Página de inicio.
    *   `/login`, `/logout`, `/register`: Autenticación de usuarios.
    *   `/dashboard`: Panel de control para administradores con estadísticas generales, incluyendo:
        *   Métricas clave (cotizaciones pendientes, facturas vencidas, productos con stock bajo).
        *   Gráficos de ventas por mes, top 5 productos más vendidos y top 5 clientes.
        *   Alertas sobre facturas vencidas y metas de ventas.
        *   KPIs como el ticket promedio, tasa de conversión y días promedio de pago.

*   **client.py (`/clients`):**
    *   `/`: Lista y busca todos los clientes.
    *   `/new`, `/<id>/edit`: Formularios para crear y editar clientes.
    *   `/<id>/delete`: Elimina un cliente.

*   **product.py (`/products`):**
    *   `/`: Lista y busca todos los productos.
    *   `/new`, `/<id>/edit`: Formularios para crear y editar productos.
    *   `/<id>/delete`: Elimina un producto.
    *   `/search`: Endpoint JSON para la búsqueda de productos con Select2.

*   **quote.py (`/quotes`):**
    *   `/`: Lista y busca todas las cotizaciones.
    *   `/new`: Crea la cabecera de una nueva cotización.
    *   `/<id>`: Vista detallada de una cotización, permite añadir ítems.
    *   `/<id>/pdf`: Genera y descarga la cotización en formato PDF.
    *   `/<id>/send_email`: Envía la cotización en PDF por correo al cliente.
    *   `/<id>/convert_to_invoice`: Crea una nueva factura a partir de una cotización existente.

*   **invoice.py (`/invoices`):**
    *   `/`: Lista y busca todas las facturas.
    *   `/new`: Crea la cabecera de una nueva factura.
    *   `/<id>`: Vista detallada de una factura, permite añadir ítems. Al añadir un ítem, se descuenta del stock del producto.
    *   `/<id>/pdf`: Genera y descarga la factura en formato PDF.
    *   `/<id>/send_email`: Envía la factura en PDF por correo al cliente.

*   **inventory.py (`/inventory`):**
    *   `/`: Muestra el stock de todos los productos y proporciona un formulario para actualizar la cantidad de stock de un producto específico.

*   **admin.py (`/admin`):**
    *   `/users`: Lista todos los usuarios registrados.
    *   `/users/<id>/edit_role`: Permite a un administrador cambiar el rol de un usuario.

## 8. Inicio del Servidor

### 8.1. Método Recomendado: `start.py`

El script `start.py` es la forma más sencilla y completa de iniciar el servidor. Incluye validaciones automáticas, detección de entorno y manejo robusto de errores.

**Uso básico:**
```bash
python start.py
```

**Opciones disponibles:**
```bash
# Modo desarrollo (por defecto)
python start.py

# Modo producción
python start.py --production

# Especificar puerto
python start.py --port 5000

# Especificar host
python start.py --host 0.0.0.0

# Solo validar configuración sin iniciar
python start.py --check

# Combinar opciones
python start.py --production --port 8080 --host 0.0.0.0
```

**Características de `start.py`:**
- ✅ Verifica dependencias antes de iniciar
- ✅ Valida la configuración del archivo `.env`
- ✅ Prueba la conexión a la base de datos
- ✅ Muestra información clara sobre la configuración
- ✅ Detecta automáticamente el entorno
- ✅ Manejo robusto de errores

### 8.2. Método Alternativo: `run.py`

Para un inicio rápido en modo desarrollo:

```bash
python run.py
```

Este script inicia el servidor en `http://127.0.0.1:5000` con modo debug activado.

### 8.3. Método Producción: `run_production.py`

Para iniciar en modo producción con Waitress:

```bash
python run_production.py
```

Este script inicia el servidor en `http://0.0.0.0:8080` con modo debug desactivado.

### 8.4. Configuración del Archivo `.env`

El archivo `.env` debe estar en la raíz del proyecto. Ejemplo de configuración:

```env
# Base de datos (sin comillas)
DATABASE_URL=mysql+mysqlconnector://usuario:contraseña@localhost:3308/nombre_base_datos

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-contraseña-de-aplicacion
MAIL_DEFAULT_SENDER=tu-email@gmail.com

# WhatsApp (opcional)
WHATSAPP_ACCESS_TOKEN=tu-token
WHATSAPP_PHONE_NUMBER_ID=tu-phone-id
WHATSAPP_BUSINESS_ACCOUNT_ID=tu-business-id
```

**Nota importante:** Las variables en `.env` NO deben tener comillas. El sistema las limpia automáticamente si las detecta, pero es mejor evitarlas.

### 8.5. Solución de Problemas al Iniciar

**Error: "Faltan dependencias"**
```bash
pip install -r requirements.txt
```

**Error: "No se puede conectar a la base de datos"**
- Verifica que MySQL esté corriendo
- Verifica las credenciales en `.env`
- Asegúrate de que la base de datos existe
- Verifica que el puerto sea correcto (ej: 3308 en lugar de 3306)

**Error: "Puerto ya en uso"**
- Cambia el puerto: `python start.py --port 5001`
- O cierra el proceso que está usando el puerto

**Validar configuración sin iniciar:**
```bash
python start.py --check
```

## 9. Sistema de Validación de Stock

El sistema incluye un sistema completo de validación de stock con las siguientes características:

### 9.1. Validaciones Implementadas

- **Validación en formularios**: Prevención de stock negativo al crear/editar productos
- **Validación en cotizaciones/facturas**: Verificación de stock disponible antes de agregar items
- **Validación en tiempo real**: Validación JavaScript que verifica stock mientras el usuario escribe
- **Validación de stock agotado**: Indicadores visuales y mensajes específicos para productos sin stock

### 9.2. Indicadores Visuales

- **Stock Agotado (0)**: Indicador rojo con icono de prohibición
- **Stock Bajo (< 5)**: Indicador naranja con icono de advertencia
- **Stock Normal**: Visualización estándar

### 9.3. Filtros de Stock

En la vista de inventario se puede filtrar por:
- Todos los productos
- Stock agotado
- Stock bajo

### 9.4. Estandarización de Tamaño de Fuente

Todas las tablas del sistema usan un tamaño de fuente estándar de `0.9rem` para mantener consistencia visual.

**Documentación detallada:** Ver `DOCUMENTACION_VALIDACION_STOCK.md` para información completa sobre el sistema de validación de stock.

## 10. Subir el Proyecto a GitHub

Para subir este proyecto a GitHub, sigue la guía completa en `GUIA_GITHUB.md`.

**Resumen rápido:**
1. Instala Git desde https://git-scm.com/download/win
2. Crea una cuenta en GitHub
3. Inicializa el repositorio: `git init`
4. Agrega archivos: `git add .`
5. Crea el primer commit: `git commit -m "Initial commit"`
6. Crea el repositorio en GitHub y conecta: `git remote add origin https://github.com/TU_USUARIO/nombre-repo.git`
7. Sube el código: `git push -u origin main`

**Archivos importantes:**
- `.gitignore` - Configurado para excluir archivos sensibles y temporales
- `.env.example` - Plantilla de configuración (se puede subir)
- `.env` - **NO se sube** (contiene información sensible)

**Ver `GUIA_GITHUB.md` para instrucciones detalladas paso a paso.**

## 11. Despachos y lectura de carnet (OCR)

El módulo de **Despachos** permite registrar entregas desde una bodega (por ejemplo minorista) a un almacén de entrega. En la pantalla de confirmar entrega existe la opción **"Leer carnet con cámara"**, que toma una foto del documento de identidad del receptor y rellena automáticamente nombre y número de documento mediante OCR.

### 11.1. Requisito opcional: Tesseract

Para que la función **"Leer carnet con cámara"** funcione, el servidor debe tener instalado **Tesseract OCR** y el paquete Python **pytesseract** (incluido en `requirements.txt`).

- **Windows:** Descargar el instalador desde [GitHub - tesseract](https://github.com/UB-Mannheim/tesseract/wiki) e instalar. Añadir Tesseract al PATH o configurar la ruta en código si es necesario.
- **Linux (Debian/Ubuntu):** `sudo apt install tesseract-ocr tesseract-ocr-spa`
- **macOS:** `brew install tesseract tesseract-lang`

El idioma español (`spa`) mejora el reconocimiento en carnets en español. Si Tesseract no está instalado, el botón "Leer carnet con cámara" seguirá visible pero al usarlo la aplicación mostrará un mensaje indicando que OCR no está disponible en el servidor; los datos del receptor pueden ingresarse manualmente.
