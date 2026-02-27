#!/bin/bash

# Se sale del script si tenemos un código no cero
set -e

# Instala las dependencias de python
pip3 install -r requirements.txt

# Recoge las static files para el proyecto
python3 manage.py collectstatic --no-input

# Revisa las migraciones de una base de datos
python3 manage.py migrate
