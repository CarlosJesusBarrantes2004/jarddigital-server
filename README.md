# 🌿 JardDigital - Backend API

Sistema de gestión para ventas, personal y liquidaciones de servicios de telecomunicaciones. Este proyecto forma parte del backend para el sistema de control de ventas de **JardDigital**.

## 🚀 Tecnologías Utilizadas

* **Lenguaje:** Python 3.12+
* **Framework:** Django 5.x
* **API:** Django REST Framework (DRF)
* **Autenticación:** JWT (JSON Web Tokens) con SimpleJWT
* **Base de Datos:** PostgreSQL
* **Entorno:** Arch Linux

## 🏗️ Arquitectura del Proyecto

El proyecto utiliza una arquitectura **MVT adaptada a API** con una capa adicional de servicios para manejar la lógica de negocio compleja (cálculos de comisiones y liquidaciones):



* **Models:** Definición de la estructura de datos en PostgreSQL.
* **Serializers:** Transformación de datos entre modelos de Python y formato JSON.
* **Views/ViewSets:** Controladores de las peticiones HTTP.
* **Services:** Lógica de negocio (Cálculos matemáticos, validaciones complejas).
* **URLs:** Definición de los endpoints de la API.

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
pip install -r requirements.txt
```
### 3. Configurar Base de Datos (PostgreSQL)
```bash
CREATE DATABASE jarddigital_db;
```
Luego, configura las credenciales en el archivo config/settings.py.

### 4. Ejecutar Migraciones
```bash
python manage.py migrate
```

## 📂 Estructura de Carpetas Principal
```bash
├── config/             # Configuración global de Django (settings, urls, wsgi)
├── apps/               # Módulos de la aplicación (Arquitectura DDD)
│   ├── core/           # Sucursales y configuraciones empresariales
│   ├── finances/       # Asistencias y reglas salariales
│   ├── sales/          # Gestión de ventas y catálogos de productos
│   ├── ubigeo/         # API geográfica de solo lectura (Departamentos, Provincias, Distritos)
│   ├── tracking/       # Ocurre semanas/meses después de la instalación (Seguimiento, Seguimiento Mensual)
│   └── users/          # Modelos de usuario, roles y serializadores de sesión
├── initial_data.json   # Backup de datos semilla para el entorno de desarrollo
└── manage.py           # Utilidad de administración de Django