from django.contrib import admin
from .models import (
    Articulo, Galpon, Lote, RegistroBajas,
    MovimientoInterno, Entidad, CabeceraTransaccion, DetalleTransaccion
)

class DetalleTransaccionInline(admin.TabularInline):
    model = DetalleTransaccion
    extra = 1

class CabeceraTransaccionAdmin(admin.ModelAdmin):
    inlines = [DetalleTransaccionInline]
    list_display = ('id_transaccion', 'tipo_operacion', 'entidad', 'fecha', 'monto_total', 'estado_pago')
    list_filter = ('tipo_operacion', 'estado_pago', 'fecha')

class LoteAdmin(admin.ModelAdmin):
    list_display = ('id_lote', 'galpon', 'raza', 'fecha_inicio', 'aves_actuales', 'estado')
    list_filter = ('estado', 'galpon')

class ArticuloAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'stock_actual', 'unidad_medida')
    list_filter = ('tipo',)

admin.site.register(Articulo, ArticuloAdmin)
admin.site.register(Galpon)
admin.site.register(Lote, LoteAdmin)
admin.site.register(RegistroBajas)
admin.site.register(MovimientoInterno)
admin.site.register(Entidad)
admin.site.register(CabeceraTransaccion, CabeceraTransaccionAdmin)
