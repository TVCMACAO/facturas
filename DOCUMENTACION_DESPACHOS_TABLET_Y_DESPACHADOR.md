# Documentación: Despachos Tablet, Rol Despachador y OCR para personas no registradas

Documentación de todo lo implementado hasta la fecha en el módulo de despachos, vista tablet, rol despachador y registro de entrega con cámara/OCR.

---

## 1. Resumen general

- **Vista despacho tablet**: interfaz simplificada y adaptada a tablet en vertical (una columna, botones grandes).
- **Bodega de origen**: para despachos desde tablet, la bodega de origen es la **bodega minorista del almacén de entrega**, asignada en el Almacén de Entrega.
- **Rol despachador**: nuevo rol de usuario con un **almacén de entrega asignado**; solo ve y gestiona despachos de ese almacén.
- **Personas no registradas**: en confirmación de entrega se puede **tomar foto del documento** con la cámara de la tablet; con **OCR** se leen nombre y número de documento, se rellenan los campos y al confirmar se **guardan en la BD** (Delivery).
- **Búsqueda de productos**: búsqueda **automática** por código, nombre o código de barras en un solo campo, sin selector "Tipo".

---

## 2. Modelos de datos

### 2.1 User (`app/models/__init__.py`)

- **assigned_delivery_point_id** (Integer, FK a `delivery_point.id`, nullable): almacén de entrega asignado al usuario cuando su rol es `despachador`.
- **role**: valores admitidos incluyen `user`, `admin`, `super_admin`, **`despachador`**.

Relación:

- `assigned_delivery_point` → `DeliveryPoint` (backref desde DeliveryPoint como `dispatchers`).

### 2.2 DeliveryPoint (`app/models/__init__.py`)

- **warehouse_id** (Integer, FK a `warehouse.id`, nullable): **bodega minorista** asociada a este almacén de entrega (origen del despacho para ese punto).
- **warehouse**: relación con `Warehouse`.
- **dispatchers**: relación con usuarios que tienen este punto asignado (`User.assigned_delivery_point_id`).

### 2.3 Delivery (`app/models/__init__.py`)

Campos usados para “a quién se entregó” (personas no registradas, rellenados por formulario o OCR):

- **recipient_name** (String 200)
- **recipient_document_number** (String 50)
- **recipient_document_type** (String 20, ej. cedula, nit)
- **delivered_at** (DateTime)

---

## 3. Base de datos y migración

### 3.1 Columnas añadidas

| Tabla            | Columna                     | Tipo     | Descripción                                      |
|------------------|-----------------------------|----------|--------------------------------------------------|
| `user`           | `assigned_delivery_point_id` | INT NULL | Almacén de entrega asignado al despachador       |
| `delivery_point` | `warehouse_id`              | INT NULL | Bodega minorista del almacén de entrega         |

### 3.2 Cómo aplicar los cambios

**Opción A – Script Python (recomendado):**

```bash
python add_despachador_column.py
```

Agrega solo `user.assigned_delivery_point_id` usando la misma configuración que la app (`.env` / `DATABASE_URL`). Si la columna ya existe, no hace nada.

**Opción B – SQL manual (MySQL):**

```sql
ALTER TABLE `user` ADD COLUMN `assigned_delivery_point_id` INT NULL;
ALTER TABLE `delivery_point` ADD COLUMN `warehouse_id` INT NULL;
```

**Opción C – Migración completa:**

```bash
python migrate_database.py
```

En `migrate_database.py` la creación de `assigned_delivery_point_id` y `warehouse_id` se ejecuta en una fase temprana para evitar errores al cargar `User`.

### 3.3 Archivos relacionados

- `add_despachador_column.py`: script mínimo para agregar `assigned_delivery_point_id` a `user`.
- `add_despachador_columns.sql`: mismo cambio en SQL para ejecutar en cliente MySQL.

---

## 4. Rol despachador y administración

### 4.1 Crear/editar usuario despachador

- En **Administración → Admin Usuarios**: al elegir rol **Despachador** aparece el campo **Almacén de entrega asignado**.
- Es obligatorio asignar un almacén de entrega para que el despachador pueda usar la vista tablet.

Archivos:

- `app/forms.py`: `AdminEditUserForm`, `AdminCreateUserForm` con rol `despachador` y campo `assigned_delivery_point_id`.
- `app/routes/admin.py`: carga y guardado de `assigned_delivery_point_id` en crear/editar usuario.
- `app/templates/admin/edit_user.html`, `create_user.html`: campo de asignación de almacén.

### 4.2 Almacén de entrega – Bodega minorista

- En **Administración → Almacenes de Entrega**, al crear o editar un almacén hay un campo **Bodega minorista asignada** (`warehouse_id`).
- Esa bodega es la que se usa como **bodega de origen** en los despachos que salen de ese almacén (p. ej. vista tablet para ese punto).

Archivos:

- `app/forms.py`: `DeliveryPointForm` con `warehouse_id`.
- `app/routes/admin.py`: crear/editar almacén de entrega con `warehouse_id`.
- `app/templates/admin/form_delivery_point.html`: selector de bodega.

### 4.3 Menú para despachador

- En `app/templates/base.html`, dentro de **Inventario**:
  - Si el usuario es **despachador**: solo se muestra el enlace **Entregas (Tablet)**.
  - Si es admin/super_admin: se muestran Ver inventario, Traslados, Despachos, Despachos (Tablet), Historial.

---

## 5. Rutas y lógica de despachos (tablet y despachador)

### 5.1 Helper `_despachador_warehouse_and_point()`

- Devuelve `(warehouse, delivery_point)` para el usuario actual si es `despachador` y tiene `assigned_delivery_point_id`.
- La bodega es `delivery_point.warehouse`; si no tiene `warehouse_id`, se toma la primera bodega minorista activa de la empresa.

### 5.2 Rutas principales

| Ruta                    | Métodos | Roles                    | Descripción |
|-------------------------|--------|---------------------------|-------------|
| `/delivery/tablet`      | GET    | admin, super_admin, despachador | Lista despachos; despachador solo los de su almacén. |
| `/delivery/tablet/start`| GET, POST | admin, super_admin, despachador | Crea despacho y redirige a edición tablet. Despachador: bodega = bodega minorista del almacén asignado. |
| `/delivery/tablet/<id>` | GET, POST | admin, super_admin, despachador | Edición simplificada para tablet; despachador solo si el despacho es de su almacén. |
| `/delivery/product-lookup` | GET  | admin, super_admin, despachador | API búsqueda de productos (código, nombre, barras; modo automático si no se envía `by`). |
| `/delivery/ocr-carnet`  | POST  | admin, super_admin, despachador | Recibe imagen del documento; devuelve nombre y número por OCR. |
| `/delivery/<id>/confirm`| GET, POST | admin, super_admin, despachador | Confirmar entrega (recipient_name, document, evidencias). |
| Resto de rutas delivery | -     | admin, super_admin y donde aplique despachador | list_deliveries, view_delivery, edit_delivery, add_delivery_item, remove_delivery_item, cancel_delivery, upload_evidence, serve_evidence. |

Para **despachador** en rutas que afectan a un despacho concreto se usa `_despachador_can_access(delivery)`: solo puede actuar sobre despachos cuyo `delivery_point_id` coincide con su `assigned_delivery_point_id`.

### 5.3 Flujo tablet (despachador)

1. Entra a **Entregas (Tablet)** → `tablet_view`.
2. Solo ve despachos de su almacén de entrega.
3. **Iniciar entrega** → `tablet_start`: se crea un despacho con bodega = bodega minorista del almacén asignado y redirección a `tablet_dispatch(id)`.
4. En `tablet_dispatch`: búsqueda de producto (automática), cantidad, añadir ítems, quitar, luego **Registrar entrega** → confirmación.
5. En confirmación: puede escribir datos a mano o usar **Leer documento con cámara** (OCR); al confirmar se guardan `recipient_*` y evidencias en la BD.

---

## 6. Plantillas

### 6.1 Vista tablet lista (`app/templates/delivery/tablet.html`)

- Diseño vertical, ancho máximo ~480px.
- Cabecera con título y, si es despachador, nombre del almacén.
- Botón principal: **Iniciar entrega** (despachador) o **Nuevo Despacho** (admin).
- Lista de despachos: enlace a editar (borrador) o ver (confirmado).
- Enlace **Volver al inicio**.

### 6.2 Edición tablet (`app/templates/delivery/tablet_dispatch.html`)

- Una columna, controles grandes.
- Campo de búsqueda: “Código, nombre o código de barras” (búsqueda automática, sin selector Tipo).
- Cantidad y botón **Añadir**.
- Lista de ítems con opción **Quitar**.
- Botón **Registrar entrega** (enlaza a confirmación).
- **Volver** a la lista tablet.
- JavaScript: búsqueda en tiempo real contra `/delivery/product-lookup` (sin parámetro `by` = automático), Enter añade si hay un solo resultado.

### 6.3 Confirmación de entrega (`app/templates/delivery/confirm.html`)

- Mensaje informativo: **Personas no registradas: use la cámara para tomar una foto del documento...**
- Campos: nombre, número y tipo de documento del receptor.
- Bloque destacado: botón **Leer documento con cámara** (sube imagen al endpoint OCR y rellena los campos).
- Al confirmar el formulario se guardan `recipient_name`, `recipient_document_number`, `recipient_document_type` y `delivered_at` en `Delivery`, más evidencias si se adjuntan.

### 6.4 Edición escritorio (`app/templates/delivery/edit.html`)

- Misma búsqueda de productos **automática** (sin selector “Tipo”); campo único “Código, nombre o código de barras (búsqueda automática)”.

---

## 7. Búsqueda de productos automática

### 7.1 API `product_lookup` (`app/routes/delivery.py`)

- Parámetros: `q` (texto), `by` (opcional), `warehouse_id` (opcional).
- Si **no se envía `by`** o `by=auto`: se busca en **código, nombre y código de barras** a la vez (cláusula OR con `ilike`).
- Si se envía `by=code`, `by=name` o `by=barcode`: se busca solo en ese campo.
- Respuesta: lista de productos (id, code, name, barcode, stock_in_warehouse si se pasó warehouse_id, etc.), límite 20.

### 7.2 Frontend

- En **tablet_dispatch** y **edit** ya no existe el selector “Tipo”; la petición a `product_lookup` se hace sin `by` para que el backend use siempre el modo automático.

---

## 8. OCR para documento del receptor

### 8.1 Endpoint `ocr_carnet` (`app/routes/delivery.py`)

- **POST**: recibe `file` (imagen) y `csrf_token`.
- Se ejecuta OCR sobre la imagen (función interna que extrae texto y aplica `_ocr_carnet_extract(text)`).
- Respuesta JSON: `recipient_name`, `recipient_document_number`, `document_type` (ej. cedula, nit).

### 8.2 Uso en confirmación

- El botón “Leer documento con cámara” abre el selector de archivo (con `capture="environment"` en móvil/tablet para usar la cámara).
- Se envía la imagen por AJAX a `/delivery/ocr-carnet` y se rellenan los campos del formulario con la respuesta; el usuario puede corregir y luego confirmar para guardar en la BD.

---

## 9. Archivos modificados o añadidos (referencia)

| Archivo | Cambios |
|--------|---------|
| `app/models/__init__.py` | User: `assigned_delivery_point_id`, rol `despachador`. DeliveryPoint: `warehouse_id`, relaciones. Delivery: recipient_* ya existentes. |
| `app/forms.py` | Rol despachador y `assigned_delivery_point_id` en formularios de usuario admin. `warehouse_id` en formulario de almacén de entrega. |
| `app/routes/admin.py` | Lógica crear/editar usuario con asignación de almacén; crear/editar almacén de entrega con bodega minorista. |
| `app/routes/delivery.py` | `_despachador_warehouse_and_point`, tablet_view, tablet_start, tablet_dispatch, product_lookup (modo auto), permisos despachador, ocr_carnet. |
| `app/templates/base.html` | Menú Inventario: despachador solo “Entregas (Tablet)”. |
| `app/templates/delivery/tablet.html` | Nueva vista lista tablet vertical. |
| `app/templates/delivery/tablet_dispatch.html` | Nueva vista edición tablet con búsqueda automática. |
| `app/templates/delivery/confirm.html` | Mensaje personas no registradas y bloque destacado cámara/OCR. |
| `app/templates/delivery/edit.html` | Eliminado selector Tipo; búsqueda automática. |
| `app/templates/admin/edit_user.html`, `create_user.html` | Campo almacén de entrega asignado para despachador. |
| `app/templates/admin/form_delivery_point.html` | Campo bodega minorista asignada. |
| `migrate_database.py` | Bloque temprano que agrega `user.assigned_delivery_point_id` y `delivery_point.warehouse_id`. |
| `add_despachador_column.py` | Script para agregar solo `user.assigned_delivery_point_id`. |
| `add_despachador_columns.sql` | SQL para agregar columnas de despachador/almacén. |

---

## 10. Resumen de pasos para dejar todo operativo

1. **Base de datos**: ejecutar `python add_despachador_column.py` o el SQL de `add_despachador_columns.sql` (y migración completa si se desea).
2. **Administración**: crear/editar un usuario con rol **Despachador** y asignarle un **Almacén de entrega**.
3. **Almacenes de entrega**: en cada almacén usado por tablet, asignar la **Bodega minorista** correspondiente.
4. **Uso**: el despachador entra por el menú **Entregas (Tablet)**, inicia entregas, agrega ítems (búsqueda automática) y en confirmación puede usar la cámara/OCR para registrar a quien se entrega y guardar en la BD.

---

*Documentación generada para el proyecto Cuentas de Cobro – módulo Despachos Tablet y Rol Despachador.*
