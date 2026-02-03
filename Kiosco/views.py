from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from Gestion.models import Lote, Articulo, MovimientoInterno, TipoMovimiento, TipoArticulo, RegistroBajas

def index(request):
    """Kiosk Home: Select Active Lote"""
    lotes = Lote.objects.filter(estado=True).order_by('galpon__nombre')
    return render(request, 'Kiosco/index.html', {'lotes': lotes})

def menu_acciones(request, lote_id):
    """Menu: Select Action for a specific Lote"""
    lote = get_object_or_404(Lote, pk=lote_id)
    return render(request, 'Kiosco/menu.html', {'lote': lote})

def registrar_consumo(request, lote_id):
    """Simplified Feed Consumption Form"""
    lote = get_object_or_404(Lote, pk=lote_id)
    # Filter only inputs (Alimentos) excluding recipe ingredients
    alimentos = Articulo.objects.filter(tipo=TipoArticulo.INSUMO, es_insumo_receta=False).order_by('nombre')
    
    if request.method == 'POST':
        articulo_id = request.POST.get('articulo')
        cantidad = request.POST.get('cantidad')
        
        if articulo_id and cantidad:
            try:
                articulo = Articulo.objects.get(pk=articulo_id)
                MovimientoInterno.objects.create(
                    lote=lote,
                    articulo=articulo,
                    tipo_movimiento=TipoMovimiento.CONSUMO,
                    cantidad=cantidad,
                    fecha=timezone.now()
                )
                messages.success(request, f'Consumo registrado: {cantidad} {articulo.unidad_medida} de {articulo.nombre}')
                return redirect('kiosco-menu', lote_id=lote.id_lote)
            except Exception as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Complete todos los campos')

    return render(request, 'Kiosco/form_consumo.html', {'lote': lote, 'alimentos': alimentos})

def registrar_produccion(request, lote_id):
    """Simplified Egg Production Form"""
    lote = get_object_or_404(Lote, pk=lote_id)
    # Filter only products (Huevos) excluding recipe ingredients (usually packaging)
    productos = Articulo.objects.filter(tipo=TipoArticulo.PRODUCTO, es_insumo_receta=False).order_by('nombre')
    
    if request.method == 'POST':
        articulo_id = request.POST.get('articulo')
        cantidad = request.POST.get('cantidad')
        
        if articulo_id and cantidad:
            try:
                articulo = Articulo.objects.get(pk=articulo_id)
                MovimientoInterno.objects.create(
                    lote=lote,
                    articulo=articulo,
                    tipo_movimiento=TipoMovimiento.PRODUCCION,
                    cantidad=cantidad,
                    fecha=timezone.now()
                )
                messages.success(request, f'Producción registrada: {cantidad} {articulo.unidad_medida} de {articulo.nombre}')
                return redirect('kiosco-menu', lote_id=lote.id_lote)
            except Exception as e:
                 messages.error(request, f'Error: {e}')
        else:
             messages.error(request, 'Complete todos los campos')

    return render(request, 'Kiosco/form_produccion.html', {'lote': lote, 'productos': productos})

def registrar_bajas(request, lote_id):
    """Simplified Mortality Form"""
    lote = get_object_or_404(Lote, pk=lote_id)
    
    if request.method == 'POST':
        cantidad = request.POST.get('cantidad')
        motivo = request.POST.get('motivo')
        
        if cantidad and motivo:
            try:
                RegistroBajas.objects.create(
                    lote=lote,
                    cantidad=cantidad,
                    motivo=motivo,
                    fecha=timezone.now()
                )
                messages.error(request, f'Baja registrada: {cantidad} aves por {motivo}') # Using error as it is a negative event, or success? Stick to success for UI feedback.
                # Actually, stick to success messages for successful actions.
                messages.success(request, f'Baja registrada: {cantidad} aves.')
                return redirect('kiosco-menu', lote_id=lote.id_lote)
            except Exception as e:
                 messages.error(request, f'Error: {e}')
        else:
             messages.error(request, 'Complete todos los campos')

    return render(request, 'Kiosco/form_bajas.html', {'lote': lote})
