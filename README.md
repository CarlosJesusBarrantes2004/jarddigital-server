# 🌿 JardDigital - Backend API

Sistema de gestión para ventas, personal y liquidaciones de servicios de telecomunicaciones. Este proyecto forma parte del backend para el sistema de control de ventas de **JardDigital**.

## 🚀 Tecnologías Utilizadas

* **Lenguaje:** Python 3.12+
* **Framework:** Django 5.x
* **API:** Django REST Framework (DRF)
* **Documentación API:** Swagger (drf-spectacular)
* **Autenticación:** JWT vía HttpOnly Cookies (Custom Authentication)
* **Base de Datos:** PostgreSQL
* **Entorno:** Arch Linux / Windows

## 🏗️ Arquitectura del Proyecto

El proyecto ha sido refactorizado para utilizar una arquitectura modular basada en contextos de negocio (DDD), separando las responsabilidades para garantizar la escalabilidad:

* **apps/users:** Gestión de identidad, roles y permisos de acceso (Autenticación JWT en Cookies).
* **apps/core:** Estructura organizacional de la empresa (Sucursales, Modalidades y Catálogos globales).
* **apps/ubigeo:** Diccionario geográfico estático del Perú (Departamentos, Provincias, Distritos).
* **apps/sales:** Motor principal de negocio (Ventas, Productos, Catálogos operativos y Audios).
* **apps/tracking:** Módulo de retención y seguimiento post-venta (Seguimiento mensual y validación de pagos).
* **apps/finances:** Módulo de RRHH y finanzas (Asistencia, Escalas de Sueldo, Liquidaciones).

## 🛠️ Configuración del Entorno de Desarrollo

### 1. Clonar el repositorio
```bash
git clone <url-del-repo>
cd jarddigital-server
```
### 2. Configurar Entorno Virtual
```bash
python -m venv venv
source venv/bin/python  # En Linux/Arch
# venv\Scripts\activate   # En Windows
pip install -r requirements.txt
```
### 3. Configurar Base de Datos (PostgreSQL)
```bash
dropdb jarddigital_db     # Solo si necesitas reiniciar una BD existente
createdb jarddigital_db
```
(Asegúrate de tener configuradas tus credenciales locales en config/settings.py o en tu archivo .env).

### 4. Ejecutar Migraciones y Cargar Datos
```bash
python manage.py migrate
python manage.py loaddata initial_data.json
```

### 5. Levantar el Servidor
```bash
python manage.py runserver
```
Visita http://127.0.0.1:8000/api/schema/swagger-ui/ para ver la documentación interactiva de la API.

## 📂 Estructura de Carpetas Principal
```bash
├── config/             # Configuración global de Django (settings, urls, wsgi)
├── apps/               # Módulos de la aplicación (Arquitectura DDD)
│   ├── core/           # Sucursales y configuraciones empresariales
│   ├── finances/       # Asistencias y reglas salariales
│   ├── sales/          # Gestión de ventas y catálogos de productos
│   ├── tracking/       # Seguimiento mensual de retención de clientes
│   ├── ubigeo/         # API geográfica de solo lectura (Departamentos, Prov, Dist)
│   └── users/          # Modelos de usuario, roles y serializadores de sesión
├── initial_data.json   # Backup de datos semilla para el entorno de desarrollo
└── manage.py           # Utilidad de administración de Django