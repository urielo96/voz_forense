from django.apps import AppConfig

# Aqui  registramos la aplicación para que Django la reconozca. El nombre debe coincidir con el nombre de la carpeta de la aplicación.

class ExtraccionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'extraccion'
