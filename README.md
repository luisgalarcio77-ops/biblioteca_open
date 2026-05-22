# MY BIBLIOTECA

Aplicación web desarrollada con Python y Flask para gestionar una biblioteca virtual. Permite registro e inicio de sesión de usuarios, administración de libros, solicitudes de préstamo, devolución de libros, reportes de ganancias y recuperación de contraseña.

## Tecnologías usadas

- Python 3.x
- Flask
- MySQL
- HTML5
- CSS3
- JavaScript
- Flask-MySQLdb
- Flask-Mail

## Características principales

- Sistema de autenticación y manejo de sesiones
- CRUD completo de libros
- Recuperación de contraseña mediante correo
- Panel de administración
- Gestión de préstamos y devoluciones
- Validaciones frontend y backend
- Diseño responsive
- Reportes de ganancias
- Interfaz moderna y dinámica

## Módulos principales

- Login y registro de usuarios
- Recuperación de contraseña
- Panel de administrador
- CRUD de libros
- Consulta de usuarios
- Solicitudes de préstamo y devolución
- Reporte de ganancias
- Visualización de libros disponibles

## Estructura del proyecto

biblioteca_open/
├── app.py
├── database.sql
├── requirements.txt
├── README.md
├── .env.example
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   ├── img/
│   └── pdfs/
└── templates/

## Instalación

1. Crear la base de datos importando `database.sql` en MySQL.

2. Crear entorno virtual:

python -m venv venv

3. Activar entorno virtual:

venv\Scripts\activate

4. Instalar dependencias:

pip install -r requirements.txt

5. Configurar variables de entorno usando `.env.example`.

6. Ejecutar el proyecto:

python app.py

7. Abrir en el navegador:

http://127.0.0.1:5000

## Administrador de prueba

Usuario: admin  
Contraseña: 12345

## Autor

Proyecto desarrollado por Maria Plaza.

## Nota

El archivo `.env.example` es solo una guía. No se deben subir credenciales reales al repositorio público.