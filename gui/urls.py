from django.urls import path, include
from . import views

urlpatterns=[
    path('', views.get_menu, name='menu'),
    path('', include('extraccion.urls')),
]