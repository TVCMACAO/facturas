# Guía para Subir el Proyecto a GitHub

## Requisitos Previos

### 1. Instalar Git

Si Git no está instalado en tu sistema, descárgalo desde:
- **Windows**: https://git-scm.com/download/win
- Durante la instalación, asegúrate de seleccionar "Add Git to PATH"

### 2. Crear una Cuenta en GitHub

Si no tienes cuenta, créala en: https://github.com

---

## Pasos para Subir el Proyecto

### Paso 1: Verificar Instalación de Git

Abre PowerShell o CMD y verifica que Git esté instalado:

```bash
git --version
```

Si muestra la versión, Git está instalado correctamente.

### Paso 2: Configurar Git (Solo la primera vez)

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-email@ejemplo.com"
```

### Paso 3: Inicializar el Repositorio Git

Navega a la carpeta del proyecto y ejecuta:

```bash
cd "E:\DESCARGAS ACTUALES\CLAUDE\PROYECTOS EN PY\CUENTAS DE COBRO"
git init
```

### Paso 4: Agregar Archivos al Repositorio

```bash
# Agregar todos los archivos (excepto los ignorados por .gitignore)
git add .

# Verificar qué archivos se van a subir
git status
```

### Paso 5: Crear el Primer Commit

```bash
git commit -m "Initial commit: Sistema de cotizaciones y facturas con validación de stock"
```

### Paso 6: Crear Repositorio en GitHub

1. Ve a https://github.com
2. Haz clic en el botón "+" (arriba a la derecha) → "New repository"
3. Nombre del repositorio: `sistema-cotizaciones-facturas` (o el nombre que prefieras)
4. Descripción: "Sistema de gestión de cotizaciones, facturas e inventario con Flask"
5. **NO marques** "Initialize this repository with a README" (ya tienes uno)
6. Haz clic en "Create repository"

### Paso 7: Conectar con GitHub y Subir

GitHub te mostrará comandos similares a estos. Ejecútalos en tu terminal:

```bash
# Agregar el repositorio remoto (reemplaza TU_USUARIO con tu usuario de GitHub)
git remote add origin https://github.com/TU_USUARIO/sistema-cotizaciones-facturas.git

# Cambiar a la rama principal (si es necesario)
git branch -M main

# Subir el código
git push -u origin main
```

**Nota:** Si GitHub te pide autenticación:
- Puedes usar un Personal Access Token en lugar de tu contraseña
- O usar GitHub Desktop (interfaz gráfica más fácil)

---

## Alternativa: Usar GitHub Desktop

Si prefieres una interfaz gráfica:

1. Descarga GitHub Desktop: https://desktop.github.com/
2. Instálalo y conéctalo con tu cuenta de GitHub
3. En GitHub Desktop:
   - File → Add Local Repository
   - Selecciona la carpeta del proyecto
   - Haz clic en "Publish repository"
   - Selecciona si quieres que sea público o privado
   - Haz clic en "Publish Repository"

---

## Archivos que NO se Subirán

Gracias al archivo `.gitignore`, estos archivos NO se subirán a GitHub:

- ✅ `venv/` - Entorno virtual (muy pesado)
- ✅ `.env` - Variables de entorno con información sensible
- ✅ `__pycache__/` - Archivos compilados de Python
- ✅ `instance/temp_pdfs/` - PDFs temporales
- ✅ `build/` y `dist/` - Archivos de compilación
- ✅ `*.db`, `*.sqlite` - Bases de datos locales
- ✅ `node_modules/` - Dependencias de Node.js

---

## Importante: Archivo .env

**⚠️ NUNCA subas el archivo `.env` a GitHub** porque contiene información sensible:
- Credenciales de base de datos
- Contraseñas de email
- Tokens de WhatsApp
- Claves secretas

El archivo `.gitignore` ya está configurado para ignorarlo.

### Crear un Archivo de Ejemplo

Ya se ha creado un archivo `.env.example` en el proyecto con valores de ejemplo. Este archivo SÍ se puede subir a GitHub como referencia para otros desarrolladores.

**Contenido del `.env.example`:**
- Configuración de base de datos
- Configuración de email
- Configuración de WhatsApp (opcional)
- Secret Key (con instrucciones para generar una)

**Para usar el archivo:**
1. Copia `.env.example` como `.env`
2. Reemplaza los valores de ejemplo con tus credenciales reales
3. El archivo `.env` NO se subirá a GitHub (está en `.gitignore`)

---

## Comandos Útiles de Git

### Ver el estado del repositorio
```bash
git status
```

### Ver qué archivos están siendo rastreados
```bash
git ls-files
```

### Agregar cambios específicos
```bash
git add nombre_archivo.py
```

### Hacer commit de cambios
```bash
git commit -m "Descripción de los cambios"
```

### Subir cambios a GitHub
```bash
git push
```

### Ver el historial de commits
```bash
git log
```

### Deshacer cambios no guardados
```bash
git restore nombre_archivo.py
```

---

## Solución de Problemas

### Error: "fatal: not a git repository"
```bash
# Asegúrate de estar en la carpeta del proyecto y ejecuta:
git init
```

### Error: "remote origin already exists"
```bash
# Elimina el remoto existente y agrégalo de nuevo:
git remote remove origin
git remote add origin https://github.com/TU_USUARIO/nombre-repositorio.git
```

### Error: "authentication failed"
- Usa un Personal Access Token en lugar de tu contraseña
- O configura SSH keys para GitHub

### Verificar qué se va a subir
```bash
# Ver archivos que se agregarán
git status

# Ver archivos que NO se agregarán (ignorados)
git status --ignored
```

---

## Recomendaciones

1. **Haz commits frecuentes** con mensajes descriptivos
2. **No subas archivos sensibles** (el `.gitignore` ayuda con esto)
3. **Crea un README.md claro** (ya lo tienes)
4. **Considera hacer el repositorio privado** si contiene información sensible
5. **Agrega una licencia** si planeas compartir el código

---

## Siguiente Paso Después de Subir

Una vez que el proyecto esté en GitHub, puedes:

1. **Agregar una descripción** en la página del repositorio
2. **Agregar temas/tags** para facilitar la búsqueda
3. **Crear Issues** para trackear mejoras o bugs
4. **Configurar GitHub Actions** para CI/CD (opcional)
5. **Agregar colaboradores** si trabajas en equipo

---

**¡Listo!** Tu proyecto estará en GitHub y podrás acceder a él desde cualquier lugar.
