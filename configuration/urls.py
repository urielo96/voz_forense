from django.contrib import admin
from django.urls import path
from extraccion import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Páginas informativas
    path('', views.inicio, name='inicio'),
    path('acerca/', views.acerca, name='acerca'),
    path('participantes/', views.participantes, name='participantes'),
    path('publicaciones/', views.publicaciones, name='publicaciones'),

    # Wizard de extracción (Módulo 1)
    path('herramienta/', views.frame1, name='frame1'),
    path('herramienta/fonemas/', views.frame2, name='frame2'),
    path('herramienta/parametros/', views.frame3, name='frame3'),
]
