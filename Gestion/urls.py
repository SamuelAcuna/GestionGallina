from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    
    # Articulos
    path('articulos/', views.articulo_list, name='articulo-list'),
    path('articulos/nuevo/', views.articulo_create, name='articulo-create'),
    path('articulos/<int:pk>/editar/', views.articulo_update, name='articulo-update'),
    path('articulos/<int:pk>/kardex/', views.articulo_kardex, name='articulo-kardex'),
    path('articulos/<int:pk>/', views.articulo_detail, name='articulo-detail'),
    path('articulos/<int:pk>/receta/', views.receta_manage, name='receta-manage'),
    path('receta/<int:pk>/eliminar/', views.receta_delete, name='receta-delete'),
    
    # Galpones
    path('galpones/', views.galpon_list, name='galpon-list'),
    path('galpones/nuevo/', views.galpon_create, name='galpon-create'),
    path('galpones/<int:pk>/editar/', views.galpon_update, name='galpon-update'),
    path('galpones/<int:pk>/eliminar/', views.galpon_delete, name='galpon-delete'),
    
    # Lotes
    path('lotes/', views.lote_list, name='lote-list'),
    path('lotes/resumen/', views.lote_overview, name='lote-overview'),
    path('lotes/nuevo/', views.lote_create, name='lote-create'),
    path('lotes/<int:pk>/', views.lote_detail, name='lote-detail'),
    path('lotes/<int:pk>/editar/', views.lote_update, name='lote-update'),
    
    # Movimientos & Bajas (linked usually from Lote Detail)
    path('movimientos/nuevo/', views.movimiento_interno_create, name='movimiento-interno-create'),
    path('bajas/nueva/', views.registro_bajas_create, name='registro-bajas-create'),
    path('vacunaciones/nueva/', views.registro_vacunacion_create, name='registro-vacunacion-create'),
    
    # Entidades
    path('entidades/', views.entidad_list, name='entidad-list'),
    path('entidades/nueva/', views.entidad_create, name='entidad-create'),
    path('entidades/<int:pk>/editar/', views.entidad_update, name='entidad-update'),
    path('entidades/<int:pk>/', views.entidad_detail, name='entidad-detail'),
    path('transacciones/', views.transaccion_list, name='transaccion-list'),
    path('transacciones/nueva/compra/', views.compra_create, name='compra-create'),
    path('transacciones/nueva/venta/', views.venta_create, name='venta-create'),
    path('transacciones/<int:pk>/editar/', views.transaccion_update, name='transaccion-update'),
    path('transacciones/<int:pk>/', views.transaccion_detail, name='transaccion-detail'),
]
