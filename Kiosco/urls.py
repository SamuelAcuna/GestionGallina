from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='kiosco-index'),
    path('lote/<int:lote_id>/', views.menu_acciones, name='kiosco-menu'),
    path('lote/<int:lote_id>/consumo/', views.registrar_consumo, name='kiosco-consumo'),
    path('lote/<int:lote_id>/produccion/', views.registrar_produccion, name='kiosco-produccion'),
    path('lote/<int:lote_id>/bajas/', views.registrar_bajas, name='kiosco-bajas'),
]
