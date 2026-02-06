# Instrucciones Rápidas para GitHub

## ✅ Lo que YA está hecho

1. ✅ Archivo `.gitignore` creado (protege archivos sensibles)
2. ✅ Script `setup_github.bat` creado (automatiza la configuración local)
3. ✅ Documentación completa en `GUIA_GITHUB.md`

## 🚀 Pasos Rápidos

### 1. Instalar Git (si no lo tienes)

**Descarga:** https://git-scm.com/download/win

**Durante la instalación:**
- ✅ Marca "Add Git to PATH"
- ✅ Usa las opciones por defecto para el resto

**Después de instalar:**
- Cierra y vuelve a abrir PowerShell/CMD
- O reinicia tu computadora

### 2. Ejecutar el Script Automático

**Opción A: Doble clic**
- Haz doble clic en `setup_github.bat`
- Sigue las instrucciones en pantalla

**Opción B: Desde terminal**
```bash
.\setup_github.bat
```

El script hará:
- ✅ Verificar que Git esté instalado
- ✅ Inicializar el repositorio Git
- ✅ Configurar tu nombre y email (si no está configurado)
- ✅ Agregar todos los archivos
- ✅ Crear el commit inicial

### 3. Crear Repositorio en GitHub

1. Ve a https://github.com
2. Haz clic en el botón **"+"** (arriba a la derecha)
3. Selecciona **"New repository"**
4. Completa:
   - **Nombre:** `sistema-cotizaciones-facturas` (o el que prefieras)
   - **Descripción:** "Sistema de gestión de cotizaciones, facturas e inventario con Flask"
   - **Visibilidad:** Público o Privado (tu elección)
   - ⚠️ **NO marques** "Initialize with README" (ya tienes uno)
5. Haz clic en **"Create repository"**

### 4. Conectar y Subir

GitHub te mostrará comandos. Ejecútalos en PowerShell/CMD:

```bash
# Reemplaza TU_USUARIO y nombre-repositorio con tus datos reales
git remote add origin https://github.com/TU_USUARIO/nombre-repositorio.git
git branch -M main
git push -u origin main
```

**Si te pide autenticación:**
- Usa un **Personal Access Token** en lugar de tu contraseña
- Crea uno en: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- O usa **GitHub Desktop** (más fácil)

---

## 🔒 Seguridad

**Archivos que NO se subirán (gracias a .gitignore):**
- ✅ `.env` - Variables de entorno con información sensible
- ✅ `venv/` - Entorno virtual (muy pesado)
- ✅ `__pycache__/` - Archivos compilados
- ✅ `instance/temp_pdfs/` - PDFs temporales
- ✅ `build/` y `dist/` - Archivos de compilación

**Archivos que SÍ se subirán:**
- ✅ Código fuente (`.py`)
- ✅ Templates (`.html`)
- ✅ `README.md`
- ✅ `requirements.txt`
- ✅ `.env.example` (plantilla sin datos reales)
- ✅ `.gitignore`

---

## ❓ Problemas Comunes

### "git no se reconoce"
- Git no está instalado o no está en el PATH
- Reinstala Git y marca "Add Git to PATH"
- Reinicia la terminal después de instalar

### "authentication failed"
- Usa un Personal Access Token en lugar de contraseña
- O instala GitHub Desktop y úsalo para subir

### "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/TU_USUARIO/nombre-repositorio.git
```

---

## 📝 Después de Subir

Una vez que el proyecto esté en GitHub:

1. **Agrega una descripción** en la página del repositorio
2. **Agrega temas/tags** para facilitar la búsqueda
3. **Considera hacerlo privado** si contiene información sensible
4. **Agrega colaboradores** si trabajas en equipo

---

**¿Necesitas ayuda?** Revisa `GUIA_GITHUB.md` para instrucciones más detalladas.
