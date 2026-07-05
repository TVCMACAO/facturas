# Manual de funcionamiento  
## Sistema de Cotizaciones, Facturas e Inventario

**Versión 1.0**  
*Fecha: Febrero 2025*

---

## 1. Introducción

Este manual está dirigido a **usuarios nuevos** del sistema. Describe cómo acceder, navegar y usar la aplicación para gestionar clientes, productos, cotizaciones, facturas e inventario (recepción, traslados y despachos) en un centro de acopio.

La aplicación permite:
- Gestionar **clientes** y **productos**.
- Crear **cotizaciones** y **facturas**, generar PDF y enviarlos por correo.
- Gestionar el **inventario**: recepción de mercancía, traslados entre secciones y despachos a puntos de entrega.
- Ver un **panel de control** (dashboard) con métricas y alertas.
- Administrar **usuarios**, **centro de acopio** y **puntos de despacho** (según el rol).

---

## 2. Acceso al sistema

### 2.1 Inicio de sesión

1. Abra el navegador y vaya a la dirección que le haya indicado su administrador (por ejemplo: `https://tu-dominio.com` o `http://localhost:5000`).
2. En la pantalla de inicio verá los campos **Usuario** y **Contraseña**.
3. Escriba su nombre de usuario y contraseña.
4. Si desea que el sistema recuerde la sesión en ese equipo, marque **Recuérdame**.
5. Pulse **Iniciar Sesión**.

Si los datos son correctos y su cuenta está activa, será redirigido al panel principal (Dashboard) o, si tiene el mismo usuario en varias empresas, a la pantalla de selección de empresa.

### 2.2 Si tiene el mismo usuario en varias empresas

Si su nombre de usuario existe en más de una empresa, después de iniciar sesión verá una pantalla para **elegir empresa**. Seleccione la empresa con la que desea trabajar y confirme. A partir de ese momento trabajará con los datos de esa empresa hasta que cierre sesión.

### 2.3 Recuperación de contraseña

1. En la pantalla de inicio de sesión, haga clic en **¿Olvidaste tu contraseña?** (o enlace similar).
2. Ingrese el **correo electrónico** con el que está registrado.
3. Recibirá un enlace por correo (revise también la carpeta de spam).
4. Haga clic en el enlace y defina una **nueva contraseña**.
5. Con la nueva contraseña ya puede iniciar sesión normalmente.

### 2.4 Cerrar sesión

En el menú lateral, en la parte inferior, encontrará el botón **Cerrar Sesión**. Al hacer clic se cierra la sesión de forma segura y se vuelve a la pantalla de inicio.

---

## 3. Roles y permisos

El sistema permite varias empresas; cada empresa tiene sus propios usuarios (con sus roles) y su propio inventario. Lo que ve cada usuario depende de su **rol**. Si no ve un menú u opción, es porque su rol no tiene permiso; en ese caso contacte al administrador.

### 3.1 Administrador general (sistema)

| Rol | Qué puede hacer |
|-----|------------------|
| **Administrador general** | Es el administrador universal del sistema: **crea empresas** y **crea los usuarios que serán administradores de empresa** de cada una. Accede al menú **Sistema** (Empresas, Todos los usuarios). No gestiona datos de negocio (ventas o inventario) de una empresa concreta; solo empresas y usuarios del sistema. |

### 3.2 Roles por empresa

| Rol | Qué puede hacer |
|-----|------------------|
| **Administrador de empresa** | Administra **una empresa**: actualiza los datos de su empresa (Mi Empresa), crea usuarios de esa empresa (todos heredan su empresa), gestiona centro de acopio y puntos de despacho. Tiene acceso completo dentro de su empresa: Dashboard, Ventas, todo Inventario y Administración (usuarios, empresa, centro de acopio, puntos de despacho). |
| **Bodega principal** | Dashboard e Inventario completo de su empresa: recepción en centro de acopio, ver inventario, traslados entre secciones (Almacén General y Farmacia), despachos y despachos en tablet, historial. No ve Ventas ni Administración. |
| **Despachador** | Dashboard e Inventario reducido: solo **Despachos (Tablet)** y **Ver inventario** de la bodega asignada. El administrador de empresa le asigna un **punto de despacho**; solo trabaja con ese punto y solo ve el inventario de esa bodega. |
| **Usuario de ventas** | Dashboard y Ventas de su empresa: clientes, productos, cotizaciones y facturas. No ve Inventario ni Administración. |

---

## 4. Navegación

- **Menú lateral:** En la izquierda hay un menú por secciones (acordeones). Según su rol verá: Principal, Ventas, Inventario, Administración y/o Sistema.
- **Empresa actual:** En la parte superior del menú se muestra el nombre de la empresa con la que está trabajando (el Administrador general no tiene empresa asignada y verá menú Sistema).
- **Móvil o tablet:** Use el botón de menú (ícono de tres líneas) para abrir o cerrar el menú lateral.
- **Mensajes del sistema:** Los avisos de éxito, error o advertencia aparecen en la parte superior del contenido. Puede cerrarlos con la X.

---

## 5. Módulos y flujos de uso

### 5.1 Principal – Dashboard

- **Menú:** Principal → Dashboard.

En el Dashboard verá:
- **Métricas:** Cotizaciones pendientes, facturas vencidas, productos con stock bajo, ventas del mes actual y comparación con el mes anterior.
- **Gráficos:** Ventas por mes, productos más vendidos, clientes destacados.
- **Accesos rápidos:** Enlaces directos a cotizaciones, facturas, clientes y productos (si su rol los permite).

---

### 5.2 Ventas

Disponible para **Administrador de empresa** y **Usuario de ventas**.

#### Clientes

- **Menú:** Ventas → Clientes.
- **Listar:** Ver todos los clientes; usar el buscador si existe.
- **Crear:** Botón “Nuevo cliente” (o similar). Complete: nombre o razón social, documento (cédula/NIT), persona de contacto, email, teléfono, WhatsApp (opcional), dirección.
- **Editar:** Desde la lista, abra el cliente y use “Editar”.

#### Productos

- **Menú:** Ventas → Productos.
- **Listar:** Ver todos los productos.
- **Crear / Editar:** Nombre, descripción, precio, stock inicial, código de barras, unidad de venta (unidad, caja, paquete) y unidades por caja/paquete si aplica.

#### Cotizaciones

- **Menú:** Ventas → Cotizaciones.
- **Crear:** Nueva cotización: seleccione cliente, fecha, IVA y tipo/valor de descuento si aplica.
- **Agregar ítems:** En la cotización, añada productos con cantidad y precio.
- **PDF:** Genere y descargue la cotización en PDF.
- **Enviar por email:** Envíe el PDF al correo del cliente.
- **Convertir a factura:** Desde una cotización puede crear una factura con los mismos datos e ítems.

#### Facturas

- **Menú:** Ventas → Facturas.
- **Crear:** Nueva factura: cliente, fecha, fecha de vencimiento, descuento e IVA.
- **Agregar ítems:** Producto, cantidad, precio. Al confirmar, se descuenta del stock.
- **PDF:** Generar y descargar factura en PDF.
- **Enviar por email:** Enviar factura al cliente.
- **Pagos y estado:** Registrar pagos y marcar la factura como pagada o no pagada. Si el sistema lo tiene habilitado, podrá gestionar **notas de crédito** desde el menú correspondiente.

---

### 5.3 Inventario

Según su rol verá todas las opciones o solo algunas (por ejemplo, despachador solo ve “Despachos (Tablet)” y “Ver inventario”).

#### Recepción

- **Menú:** Inventario → Recepción.
- **Quién:** Administrador de empresa, Bodega principal.
- **Uso:** Registrar la entrada de mercancía al centro de acopio (desde transportista o proveedor).
- **Flujo:**
  1. **Nueva recepción:** Crear recepción y elegir la **sección** de destino (Almacén General o Farmacia).
  2. **Agregar ítems:** Producto y cantidad recibida.
  3. Guardar y, si aplica, confirmar la recepción.
- Desde el listado puede ver y editar recepciones en curso.

#### Ver inventario

- **Menú:** Inventario → Ver inventario.
- Muestra el stock de productos por bodega/sección. Suele haber filtros (todos, stock bajo, agotado) para localizar productos con poco stock.

#### Traslados

- **Menú:** Inventario → Traslados.
- **Quién:** Administrador de empresa, Bodega principal.
- **Uso:** Mover mercancía **entre secciones** del mismo centro de acopio (por ejemplo de Almacén General a Farmacia o al revés).
- **Flujo:** Crear traslado (sección origen, sección destino), agregar ítems y cantidades, guardar y confirmar.

#### Despachos

- **Menú:** Inventario → Despachos.
- **Uso:** Registrar la salida de mercancía desde una **sección** del centro de acopio hacia un **punto de despacho** (por ejemplo un local o farmacia).
- **Estados:** Borrador (editable), Confirmado, Anulado.
- **Flujo:** Crear despacho (sección origen, punto de despacho), agregar ítems; en borrador puede editar; al confirmar se registra la salida de stock. En la confirmación puede haber opción **“Leer carnet con cámara”** para llenar datos del receptor con OCR (si el servidor tiene Tesseract instalado); si no, se ingresan manualmente.

#### Despachos (Tablet)

- **Menú:** Inventario → Despachos (Tablet).
- **Uso:** Flujo simplificado para realizar despachos desde una tablet. El usuario **minorista** solo ve y trabaja con su **punto de despacho asignado**; los demás roles pueden elegir sección y punto según configuración.

#### Historial

- **Menú:** Inventario → Historial.
- Consulta de movimientos de inventario: recepciones, traslados, despachos y ventas (facturas) para auditoría y seguimiento.

---

### 5.4 Administración

Solo visible para **Administrador de empresa**.

#### Admin Usuarios

- **Menú:** Administración → Admin Usuarios.
- Listar usuarios de la empresa, **crear** usuario (nombre, usuario, email, contraseña, rol y, si es despachador, **punto de despacho asignado**) y **editar** o desactivar usuarios.

#### Mi Empresa

- **Menú:** Administración → Mi Empresa.
- Ver y editar los datos de la empresa (nombre, NIT, dirección, etc., según lo configurado).

#### Centro de acopio

- **Menú:** Administración → Centro de acopio.
- Gestionar las **secciones** del centro de acopio (por ejemplo Almacén General y Farmacia). Para cada sección: nombre, código, tipo (Almacén General / Farmacia), dirección y si está activa o inactiva. Listado compacto con opción “Nueva sección” y “Editar”.

#### Puntos de despacho

- **Menú:** Administración → Puntos de despacho.
- Gestionar los **puntos de despacho** (lugares a los que se envía mercancía). Para cada punto: nombre, código, dirección, **sección por defecto** desde la que se despacha y si está activo. Crear y editar según necesidad.

---

### 5.5 Sistema (Administrador general)

Solo visible para **Administrador general**.

- **Empresas:** Listar y gestionar todas las empresas del sistema.
- **Todos los usuarios:** Listar usuarios de todas las empresas para administración global.

---

## 6. Glosario de términos

| Término | Significado |
|--------|-------------|
| **Centro de acopio** | Conjunto de almacenes (secciones) donde se recibe y guarda la mercancía antes de despacharla. |
| **Sección** | Cada almacén dentro del centro de acopio; por ejemplo **Almacén General** y **Farmacia**. |
| **Punto de despacho** | Lugar de destino al que se envía mercancía desde una sección (local, farmacia, etc.). |
| **Recepción** | Entrada de mercancía desde transportista o proveedor a una sección del centro de acopio. |
| **Traslado** | Movimiento de mercancía entre dos secciones del mismo centro de acopio. |
| **Despacho** | Salida de mercancía desde una sección hacia un punto de despacho (entrega al receptor). |

---

## 7. Solución de problemas frecuentes

- **No puedo iniciar sesión:** Verifique usuario y contraseña. Si sigue fallando, confirme con el administrador que su cuenta está activa.
- **Me pide elegir empresa:** Su usuario está asociado a más de una empresa; elija con cuál desea trabajar en esa sesión. |
- **No veo el menú de Ventas o Inventario:** Depende de su rol. Si cree que debería ver algo que no aparece, contacte al administrador. |
- **Olvidé mi contraseña:** Use el enlace “¿Olvidaste tu contraseña?” en la pantalla de inicio e ingrese su correo; revise también la carpeta de spam. |
- **El botón “Leer carnet con cámara” no hace nada o da error:** La función requiere que en el servidor esté instalado Tesseract OCR. Mientras tanto, ingrese nombre y documento del receptor manualmente. |

---

## 8. Contacto y soporte

Para solicitar nuevos permisos, cambios de rol o reportar fallos, contacte al **administrador de su empresa** o al responsable de sistemas que le haya proporcionado el acceso.

---

*Fin del manual.*
