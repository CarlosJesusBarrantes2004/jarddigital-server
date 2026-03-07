#!/usr/bin/env bash
# Terminar la ejecución si algún comando falla
set -o errexit

echo "Instalando dependencias..."
pip install -r requirements.txt

echo "Recolectando archivos estáticos (Panel de Admin)..."
python manage.py collectstatic --no-input

echo "Aplicando migraciones a la Base de Datos..."
python manage.py migrate