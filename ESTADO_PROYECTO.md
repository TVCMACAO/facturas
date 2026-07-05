# Estado del proyecto – Cuentas de Cobro

**Última actualización:** 5 de julio de 2026

## Mejoras recientes (julio 2026)

- Corrección de `convert_to_invoice`: numeración por empresa, POST con CSRF, rollback en errores.
- Helper `app/numbering.py` para números de factura.
- CSRF global (`CSRFProtect`), `ProductionConfig` con `SECRET_KEY` obligatoria.
- Migraciones fuera del arranque de la app (`migrate_database.py` manual).
- Endpoint `/health`, `.env.example`, tests pytest en `tests/`.
- Eliminación de instrumentación de depuración y `ocr_capture.json`.

Este documento resume en qué punto quedó el proyecto para retomarlo con contexto claro.

---

## 1. Qué es el proyecto

- **Nombre del repo/carpeta:** Cuentas de Cobro  
- **Nombre en la UI:** "Cotizador" (sidebar: *Cotizador*)  
- **Tipo:** Aplicación web Flask para gestión de clientes, productos, cotizaciones, facturas, notas de crédito, inventario multi-almacén, despachos y recepción. Multi-tenant por empresa, con roles y tokens en rutas.

---

## 2. Stack y estructura

| Aspecto | Detalle |
|--------|---------|
| **Backend** | Python, Flask |
| **ORM / BD** | SQLAlchemy, MySQL (`mysql-connector-python`) |
| **Auth** | Flask-Login, roles por usuario |
| **Formularios** | Flask-WTF (WTForms) |
| **PDF** | WeasyPrint |
| **Email** | Flask-Mail |
| **i18n** | Flask-Babel (es) |
| **Config** | `config.py` + `.env` (python-dotenv) |

- **Arranque recomendado:** `python start.py` (desarrollo) o `python start.py --production`.
- **Documentación general:** `README.md`, `MANUAL_USUARIO.md`, `GUIA_GITHUB.md`.

---

## 3. Módulos implementados (resumen)

### 3.1 Ventas (Principal)

- **Clientes** (`/clients`): listado, búsqueda, crear, editar, eliminar.
- **Productos** (`/products`): listado, búsqueda, crear, editar, eliminar; búsqueda JSON para Select2.
- **Cotizaciones** (`/quotes`): listado con filtros, crear, detalle con ítems, PDF, envío por email, convertir a factura. Estados: pendiente, aceptada, rechazada, vencida, facturada.
- **Facturas** (`/invoices`): listado con filtros, crear, detalle con ítems (descuento de stock), PDF, envío por email. Estados: borrador, no_pagada, parcial, pagada, vencida, anulada. Pagos y métodos de pago.
- **Notas de crédito** (`/credit_notes`): blueprint registrado; listado, crear desde factura, ítems, PDF, eliminación; devolución de stock vía `InventoryMovement` con `reference_type='credit_note'`.

### 3.2 Inventario

- **Ver inventario** (`/inventory`): stock por producto; filtros (todos, sin stock, stock bajo); actualización de cantidades.
- **Historial** (`/inventory/history`): movimientos (venta, compra, ajuste, devolución) con filtros.
- **Traslados** (`/transfers`): entre almacenes; estados borrador, confirmado, anulado.
- **Recepción** (`/receptions`): recepción de mercancía (roles admin/bodega_principal).
- **Pedidos de despacho** (`/dispatch_orders`): pedidos por punto de entrega; estados pendiente, en_preparacion, enviado, recibido. Vista “Pedidos pendientes” con badge en el menú.
- **Despachos** (`/deliveries`): creación desde pedido, lista, detalle; vista **Tablet** para confirmar entrega (incl. “Leer carnet con cámara” OCR si Tesseract está instalado).
- **Stock por punto de despacho:** `ProductDeliveryPointStock` (inventario independiente por almacén de entrega).

### 3.3 Multi-tenant y roles

- **Empresas:** modelo `Company` con `CompanyConfig` (prefijos factura, cotización, nota de crédito, etc.).
- **Usuarios:** `User` con `company_id`; mismo `username` puede existir en distintas empresas.
- **Roles:**  
  `super_admin` (sistema: empresas, todos los usuarios), `admin` (empresa: usuarios, mi empresa, almacenes, puntos de despacho), `bodega_principal`, `despachador`, `user` (ventas).
- **Filtrado por empresa:** `filter_by_company()` en consultas; `company_id` en tablas principales (client, product, quote, invoice, credit_note, etc.).

### 3.4 Seguridad y navegación

- **Tokens en rutas:** rutas sensibles requieren `token` en query; `url_with_token()` en plantillas; `require_route_token` en `before_request`.
- **Tokens de vista:** para enlaces de solo lectura (ej. PDF/email) con `view_token` y validación por tiempo.
- **Decoradores:** `@login_required`, `@role_required` (p. ej. admin, super_admin).

### 3.5 Administración

- **Admin de empresa:** usuarios de la empresa, “Mi Empresa” (configuración), almacenes (centro de acopio), puntos de despacho.
- **Super admin:** listado de empresas, crear empresa (y opcionalmente admin), “Todos los Usuarios”.
- **Dashboard:** métricas (cotizaciones pendientes, facturas vencidas, stock bajo), gráficos, KPIs, total/monto notas de crédito.

---

## 4. Interfaz (base.html)

- **Layout:** sidebar fijo izquierdo (verde), acordeón por sección, responsive con botón hamburguesa y overlay en &lt; 992px.
- **Secciones del menú (según rol):**
  - **Principal:** Dashboard.
  - **Ventas:** Clientes, Productos, Cotizaciones, Facturas.  
    (No hay ítem de menú para “Notas de crédito”; el módulo existe en `/credit_notes`.)
  - **Inventario:** según rol (despachador: Mis pedidos, Solicitar productos, Despachos Tablet, Ver inventario; otros: Recepción si aplica, Ver inventario, Traslados, Pedidos pendientes, Despachos, Despachos Tablet, Historial).
  - **Administración** (admin): Admin Usuarios, Mi Empresa, Administración de almacenes, Puntos de despacho.
  - **Sistema** (super_admin): Empresas, Todos los Usuarios.
- **Flash messages:** estilos tipo tarjeta (success, danger, warning, info), auto-cierre ~5 s.
- **Tablas:** fuente estándar 0.9rem en celdas.

---

## 5. Punto en el que quedamos / Pendientes detectados

1. **Notas de crédito sin enlace en el menú**  
   El blueprint `credit_notes` está registrado y las rutas funcionan (`/credit_notes/`), pero en `app/templates/base.html` no hay enlace en el acordeón “Ventas” a “Notas de crédito”. Para dejarlo visible habría que añadir algo como:
   - En la sección Ventas:  
     `<a href="{{ url_with_token('credit_notes.list_credit_notes') }}">...</a> Notas de crédito`

2. **Documentación ya existente**  
   - `README.md`: descripción general, configuración, arranque, estructura.  
   - `MANUAL_USUARIO.md`: uso por roles.  
   - `DOCUMENTACION_VALIDACION_STOCK.md`: validación de stock.  
   - `DOCUMENTACION_DESPACHOS_TABLET_Y_DESPACHADOR.md`: despachos, tablet, rol despachador, OCR.  
   - `RESUMEN_VERIFICACION_COMPANIAS.md`: verificación de `company_id`.  
   - `GUIA_GITHUB.md` / `INSTRUCCIONES_GITHUB_RAPIDAS.md`: subida a GitHub.

3. **No hay TODOs/FIXMEs críticos** en el código que indiquen una tarea a medio hacer; los “pendiente” que aparecen son mayormente etiquetas de estado (ej. “Pedidos pendientes”) o opciones de filtro (“Todos”), no tareas abiertas.

4. **Migraciones**  
   Hay scripts y SQL de migración (roles, `company_id`, despachos, columnas varias). Si se retoma en otro entorno, conviene revisar `migrate_database.py` y los `.sql` según la versión actual de la BD.

---

## 6. Cómo retomar

- **Desarrollo:** `python start.py` (o `run.py`). Revisar `.env` (BD, mail, opcional WhatsApp).
- **Si se quiere exponer “Notas de crédito” en la UI:** añadir el enlace en `base.html` dentro del acordeón Ventas (ver punto 5.1).
- **Para recordar funcionalidad por módulo:** usar este archivo + `README.md` + `MANUAL_USUARIO.md` y los DOCUMENTACION_*.md según el área (stock, despachos, empresas).

Si quieres, el siguiente paso puede ser solo añadir el enlace de Notas de crédito en el menú y dejarlo documentado aquí.
