from django.urls import path

from . import views

app_name = 'spdb'

urlpatterns = [
    path('', views.index, name='index')
]