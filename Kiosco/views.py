from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from Gestion.models import Lote, Articulo, MovimientoInterno, TipoMovimiento, TipoArticulo, RegistroBajas

from django.db.models import Sum

def index(request):
    """Kiosk Home: Select Active Lote with Daily Stats"""
    lotes = Lote.objects.filter(estado=True).order_by('galpon__nombre')
    today = timezone.now()
    
    lotes_stats = []
    for lote in lotes:
        # Calculate daily aggregates
        prod = MovimientoInterno.objects.filter(
            lote=lote, 
            tipo_movimiento=TipoMovimiento.PRODUCCION, 
            fecha__date=today
        ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        cons = MovimientoInterno.objects.filter(
            lote=lote, 
            tipo_movimiento=TipoMovimiento.CONSUMO, 
            fecha__date=today
        ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        bajas = RegistroBajas.objects.filter(
            lote=lote, 
            fecha__date=today
        ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        lotes_stats.append({
            'lote': lote,
            'produccion_hoy': int(prod),
            'consumo_hoy': cons,
            'bajas_hoy': int(bajas)
        })

    return render(request, 'Kiosco/index.html', {'lotes_stats': lotes_stats})

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
        print(f"DEBUG: POST data - articulo: {articulo_id}, cantidad: {cantidad}")
        
        if articulo_id and cantidad:
            try:
                articulo = Articulo.objects.get(pk=articulo_id)
                mov = MovimientoInterno.objects.create(
                    lote=lote,
                    articulo=articulo,
                    tipo_movimiento=TipoMovimiento.CONSUMO,
                    cantidad=cantidad,
                    fecha=timezone.now()
                )
                print(f"DEBUG: Created {mov} with amount {mov.cantidad}")
                messages.success(request, f'Consumo registrado: {cantidad} {articulo.unidad_medida} de {articulo.nombre}')
                return redirect('kiosco-menu', lote_id=lote.id_lote)
            except Exception as e:
                print(f"DEBUG: Error creating consumption: {e}")
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Complete todos los campos')

    # Daily Movements Context
    movimientos = MovimientoInterno.objects.filter(
        lote=lote, 
        tipo_movimiento=TipoMovimiento.CONSUMO,
        fecha__date=timezone.now()
    ).order_by('-fecha')

    return render(request, 'Kiosco/form_consumo.html', {'lote': lote, 'alimentos': alimentos, 'movimientos': movimientos})

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

    # Daily Stats Context
    movimientos = MovimientoInterno.objects.filter(
        lote=lote, 
        tipo_movimiento=TipoMovimiento.PRODUCCION,
        fecha__date=timezone.now()
    ).order_by('-fecha')
    print(movimientos)
    return render(request, 'Kiosco/form_produccion.html', {'lote': lote, 'productos': productos, 'movimientos': movimientos})

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

    # Daily Stats Context
    movimientos = RegistroBajas.objects.filter(
        lote=lote,
        fecha__date=timezone.now()
    ).order_by('-fecha')

    return render(request, 'Kiosco/form_bajas.html', {'lote': lote, 'movimientos': movimientos})

# --- EDIT VIEWS ---

def movimiento_edit(request, pk):
    movimiento = get_object_or_404(MovimientoInterno, pk=pk)
    lote = movimiento.lote
    
    if request.method == 'POST':
        cantidad = request.POST.get('cantidad')
        # Allow article change? Maybe only for production/consumption mismatch. For now just quantity.
        if cantidad:
            movimiento.cantidad = cantidad
            movimiento.save()
            messages.success(request, 'Registro actualizado.')
            return redirect('kiosco-menu', lote_id=lote.id_lote)
    
    return render(request, 'Kiosco/movimiento_edit.html', {'movimiento': movimiento, 'lote': lote})

def baja_edit(request, pk):
    baja = get_object_or_404(RegistroBajas, pk=pk)
    lote = baja.lote
    
    if request.method == 'POST':
        cantidad = request.POST.get('cantidad')
        motivo = request.POST.get('motivo')
        
        if cantidad and motivo:
            baja.cantidad = cantidad
            baja.motivo = motivo
            baja.save()
            messages.success(request, 'Baja actualizada.')
            return redirect('kiosco-menu', lote_id=lote.id_lote)
            
    return render(request, 'Kiosco/baja_edit.html', {'baja': baja, 'lote': lote})
