from django.apps import AppConfig
import os

class DelaysConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'delays'
    path = os.path.dirname(os.path.abspath(__file__))
