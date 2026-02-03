from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.db.models import Sum
from django.utils import timezone
import datetime
from .models import Articulo, Galpon, Lote, RegistroBajas, MovimientoInterno, Entidad, CabeceraTransaccion, RegistroVacunacion, TipoMovimiento, Receta, DetalleTransaccion, TipoOperacion
from .forms import (
    ArticuloForm, GalponForm, LoteForm, RegistroBajasForm, MovimientoInternoForm,
    EntidadForm, CabeceraTransaccionForm, DetalleTransaccionFormSet, RegistroVacunacionForm, RecetaForm
)

def index(request):
    """Dashboard View"""
    total_aves = Lote.objects.filter(estado=True).aggregate(Sum('aves_actuales'))['aves_actuales__sum'] or 0
    # Lote Status Logic
    lotes_activos = Lote.objects.filter(estado=True).count()
    alertas_stock = Articulo.objects.filter(controlar_stock=True, stock_actual__lte=models.F('stock_minimo'))
    
    lotes = Lote.objects.filter(estado=True).order_by('galpon__nombre')
    today = timezone.now().date()
    start_of_day = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
    end_of_day = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))

    lotes_status = []
    for lote in lotes:
        # Get ALL feed consumption for today
        consumos_hoy = MovimientoInterno.objects.filter(
            lote=lote, 
            tipo_movimiento=TipoMovimiento.CONSUMO,
            fecha__range=(start_of_day, end_of_day)
        ).order_by('fecha')
        
        alimentado = consumos_hoy.exists()
        detalles_alim = []
        for consumo in consumos_hoy:
            detalles_alim.append({
                'cantidad': consumo.cantidad,
                'unidad': consumo.articulo.unidad_medida,
                'nombre': consumo.articulo.nombre,
                'hora': consumo.fecha  # DateTime object
            })

        lotes_status.append({
            'lote': lote,
            'alimentado_hoy': alimentado,
            'detalles': detalles_alim
        })

    context = {
        'total_aves': total_aves,
        'lotes_activos': lotes_activos,
        'alertas_stock': alertas_stock,
        'lotes_status': lotes_status,
    }
    return render(request, 'Gestion/index.html', context)

# --- ARTICULOS ---

def articulo_list(request):
    articulos = Articulo.objects.all()
    return render(request, 'Gestion/articulo_list.html', {'articulos': articulos})

def articulo_create(request):
    if request.method == 'POST':
        form = ArticuloForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Artículo creado exitosamente.')
            return redirect('articulo-list')
    else:
        form = ArticuloForm()
    return render(request, 'Gestion/articulo_form.html', {'form': form, 'title': 'Nuevo Artículo'})

    return render(request, 'Gestion/articulo_form.html', {'form': form, 'title': 'Nuevo Artículo'})

def articulo_update(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    
    # Recipe Logic (merged here)
    recetas = Receta.objects.filter(producto=articulo)
    receta_form = RecetaForm()

    if request.method == 'POST':
        if 'btn_update_article' in request.POST:
            form = ArticuloForm(request.POST, instance=articulo)
            if form.is_valid():
                form.save()
                messages.success(request, 'Artículo actualizado exitosamente.')
                return redirect('articulo-list')
        elif 'btn_add_ingredient' in request.POST:
            receta_form = RecetaForm(request.POST)
            if receta_form.is_valid():
                receta = receta_form.save(commit=False)
                receta.producto = articulo
                receta.save()
                messages.success(request, 'Ingrediente agregado.')
                return redirect('articulo-update', pk=pk)
            else:
                form = ArticuloForm(instance=articulo) # Restore main form
    else:
        form = ArticuloForm(instance=articulo)
        
    return render(request, 'Gestion/articulo_form.html', {
        'form': form, 
        'title': 'Editar Artículo',
        'articulo': articulo,
        'recetas': recetas,
        'receta_form': receta_form
    })

def articulo_detail(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    return render(request, 'Gestion/articulo_detail.html', {'articulo': articulo, 'title': articulo.nombre})

def articulo_kardex(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    
    # Unified List from LogArticulo (Real Kardex)
    history = articulo.logs.all().order_by('-fecha')
    
    return render(request, 'Gestion/articulo_kardex.html', {
        'articulo': articulo,
        'history': history
    })

# Remove standalone receta_manage if no longer needed, or keep for direct access?
# Keeping receta_delete as it is used by the form actions


def receta_manage(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    recetas = Receta.objects.filter(producto=articulo)
    
    if request.method == 'POST':
        form = RecetaForm(request.POST)
        if form.is_valid():
            receta = form.save(commit=False)
            receta.producto = articulo
            receta.save()
            messages.success(request, 'Ingrediente agregado a la receta.')
            return redirect('receta-manage', pk=pk)
    else:
        form = RecetaForm()
        
    return render(request, 'Gestion/receta_form.html', {
        'articulo': articulo,
        'recetas': recetas,
        'form': form
    })

def receta_delete(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    producto_pk = receta.producto.pk
    receta.delete()
    messages.success(request, 'Ingrediente eliminado de la receta.')
    return redirect('receta-manage', pk=producto_pk)

# --- GALPONES ---

def galpon_list(request):
    galpones = Galpon.objects.all()
    return render(request, 'Gestion/galpon_list.html', {'galpones': galpones})

def galpon_create(request):
    if request.method == 'POST':
        form = GalponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Galpón creado exitosamente.')
            return redirect('galpon-list')
    else:
        form = GalponForm()
    return render(request, 'Gestion/galpon_form.html', {'form': form, 'title': 'Nuevo Galpón'})

def galpon_update(request, pk):
    galpon = get_object_or_404(Galpon, pk=pk)
    if request.method == 'POST':
        form = GalponForm(request.POST, instance=galpon)
        if form.is_valid():
            form.save()
            messages.success(request, 'Galpón actualizado exitosamente.')
            return redirect('galpon-list')
    else:
        form = GalponForm(instance=galpon)
    return render(request, 'Gestion/galpon_form.html', {'form': form, 'title': 'Editar Galpón'})

def galpon_delete(request, pk):
    galpon = get_object_or_404(Galpon, pk=pk)
    if request.method == 'POST':
        galpon.delete()
        messages.success(request, 'Galpón eliminado.')
        return redirect('galpon-list')
    return render(request, 'Gestion/confirm_delete.html', {'object': galpon, 'cancel_url': 'galpon-list'})

# --- BIOLOGICAL CYCLE ---

def lote_list(request):
    lotes = Lote.objects.all().order_by('-estado', 'galpon__nombre')
    return render(request, 'Gestion/lote_list.html', {'lotes': lotes})

def lote_create(request):
    if request.method == 'POST':
        form = LoteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote iniciado exitosamente.')
            return redirect('lote-list')
    else:
        form = LoteForm()
    return render(request, 'Gestion/lote_form.html', {'form': form, 'title': 'Nuevo Lote'})

def lote_detail(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    bajas = RegistroBajas.objects.filter(lote=lote).order_by('-fecha')
    movimientos = MovimientoInterno.objects.filter(lote=lote).order_by('-fecha')
    vacunaciones = RegistroVacunacion.objects.filter(lote=lote).order_by('-fecha')
    return render(request, 'Gestion/lote_detail.html', {
        'lote': lote,
        'bajas': bajas,
        'movimientos': movimientos,
        'vacunaciones': vacunaciones
    })

def lote_update(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    if request.method == 'POST':
        form = LoteForm(request.POST, instance=lote)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote actualizado.')
            return redirect('lote-list')
    else:
        form = LoteForm(instance=lote)
    return render(request, 'Gestion/lote_form.html', {'form': form, 'title': 'Editar Lote'})

def lote_overview(request):
    """Macro view of all active lots with last 5 days summary"""
    lotes = Lote.objects.filter(estado=True).order_by('galpon__nombre')
    
    # Range of last 5 days
    today = timezone.now().date()
    dates = [today - timezone.timedelta(days=i) for i in range(5)]
    
    lote_data = []
    
    for lote in lotes:
        daily_stats = []
        for d in dates:
            # Filter movements for this day/lote
            movs = MovimientoInterno.objects.filter(lote=lote, fecha=d)
            
            produccion = movs.filter(tipo_movimiento=TipoMovimiento.PRODUCCION).aggregate(total=Sum('cantidad'))['total'] or 0
            consumo = movs.filter(tipo_movimiento=TipoMovimiento.CONSUMO).aggregate(total=Sum('cantidad'))['total'] or 0
            
            daily_stats.append({
                'date': d,
                'produccion': produccion,
                'consumo': consumo
            })
            
        lote_data.append({
            'lote': lote,
            'stats': daily_stats
        })
        
    return render(request, 'Gestion/lote_overview.html', {'lote_data': lote_data})

# --- REGISTRO BAJAS, MOVIMIENTOS, VACUNAS ---

def registro_bajas_create(request):
    initial_lote = request.GET.get('lote_id')
    form = RegistroBajasForm(initial={'lote': initial_lote} if initial_lote else None)
    
    if request.method == 'POST':
        form = RegistroBajasForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Baja registrada correctamente.')
            return redirect('lote-detail', pk=form.cleaned_data['lote'].pk)
            
    return render(request, 'Gestion/registro_bajas_form.html', {'form': form, 'title': 'Registrar Baja'})

def movimiento_interno_create(request):
    initial_lote = request.GET.get('lote_id')
    form = MovimientoInternoForm(initial={'lote': initial_lote} if initial_lote else None)

    if request.method == 'POST':
        form = MovimientoInternoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Movimiento registrado correctamente.')
                return redirect('lote-detail', pk=form.cleaned_data['lote'].pk)
            except Exception as e:
                 messages.error(request, f'Error al registrar movimiento: {e}')
    
    return render(request, 'Gestion/movimiento_interno_form.html', {'form': form, 'title': 'Registrar Movimiento'})

def registro_vacunacion_create(request):
    initial_lote = request.GET.get('lote_id')
    form = RegistroVacunacionForm(initial={'lote': initial_lote} if initial_lote else None)

    if request.method == 'POST':
        form = RegistroVacunacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vacunación registrada correctamente.')
            return redirect('lote-detail', pk=form.cleaned_data['lote'].pk)
    
    return render(request, 'Gestion/registro_vacunacion_form.html', {'form': form, 'title': 'Registrar Vacunación'})

# --- COMMERCIAL CYCLE ---

# Entidades
def entidad_list(request):
    entidades = Entidad.objects.all()
    return render(request, 'Gestion/entidad_list.html', {'entidades': entidades})

def entidad_create(request):
    if request.method == 'POST':
        form = EntidadForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entidad creada.')
            return redirect('entidad-list')
    else:
        form = EntidadForm()
    return render(request, 'Gestion/entidad_form.html', {'form': form, 'title': 'Nueva Entidad'})

def entidad_update(request, pk):
    entidad = get_object_or_404(Entidad, pk=pk)
    if request.method == 'POST':
        form = EntidadForm(request.POST, instance=entidad)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entidad actualizada.')
            return redirect('entidad-list')
    else:
        form = EntidadForm(instance=entidad)
    return render(request, 'Gestion/entidad_form.html', {'form': form, 'title': 'Editar Entidad'})

def entidad_detail(request, pk):
    entidad = get_object_or_404(Entidad, pk=pk)
    return render(request, 'Gestion/entidad_detail.html', {'entidad': entidad, 'title': entidad.nombre_razon_social})

def transaccion_list(request):
    transacciones = CabeceraTransaccion.objects.all().order_by('-fecha')
    return render(request, 'Gestion/transaccion_list.html', {'transacciones': transacciones})

# Shared logic helper
def procesar_transaccion(request, tipo_operacion, template_name, title):
    if request.method == 'POST':
        form = CabeceraTransaccionForm(request.POST)
        formset = DetalleTransaccionFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                # 1. Save Header
                transaccion = form.save(commit=False)
                transaccion.tipo_operacion = tipo_operacion
                transaccion.monto_total = 0 # Will be updated by signals
                transaccion.save()
                
                # 2. Save Details
                detalles = formset.save(commit=False)
                for detalle in detalles:
                    detalle.transaccion = transaccion
                    detalle.save() # Signal triggers stock update and total calc
                    
                    # 3. Update Base Price Logic
                    # Check if "update_price_X" checkbox is present in POST data for this form index
                    # Requires matching form prefix. 
                    # Simpler approach: If 'update_base_price' is in POST (global) or per item?
                    # Let's assume per-item checkbox in the row. 
                    # Name format: form-0-update_price
                    
                    prefix = detalle.prefix # e.g. form-0
                    if request.POST.get(f'{prefix}-update_price'):
                        articulo = detalle.articulo
                        # If Purchase, ref price is cost. If Sale, ref price is sale price.
                        # Usually we update ref price on Purchase (Cost) or if explicitly set on Sale.
                        # Let's just update perfectly to what was entered.
                        if articulo.precio_referencia != detalle.precio_unitario:
                            old_price = articulo.precio_referencia
                            articulo.precio_referencia = detalle.precio_unitario
                            articulo.save() # Triggers metadata log signal? Yes.
                            
                            # Explicit Log for clarity
                            from .signals import create_log_entry
                            create_log_entry(
                                articulo, 'EDICION', 0, 
                                articulo.stock_actual, articulo.stock_actual,
                                f"Precio Base actualizado vía {title}: {old_price} -> {articulo.precio_referencia}"
                            )

                messages.success(request, f'{title} registrada exitosamente.')
                return redirect('transaccion-list')
            except Exception as e:
                messages.error(request, f'Error al guardar: {e}')
                return render(request, template_name, {
                    'form': form, 'formset': formset, 'title': title, 'tipo': tipo_operacion
                })
        else:
             messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = CabeceraTransaccionForm()
        # Filter entities based on type
        if tipo_operacion == TipoOperacion.COMPRA:
            form.fields['entidad'].queryset = Entidad.objects.filter(es_proveedor=True)
        else:
            form.fields['entidad'].queryset = Entidad.objects.filter(es_cliente=True)
            
        formset = DetalleTransaccionFormSet()

    # Pass Article Prices for JS
    import json
    precios = {a.id_articulo: str(a.precio_referencia) for a in Articulo.objects.all()}

    return render(request, template_name, {
        'form': form, 
        'formset': formset, 
        'title': title,
        'tipo': tipo_operacion,
        'precios_json': json.dumps(precios)
    })

def compra_create(request):
    return procesar_transaccion(request, TipoOperacion.COMPRA, 'Gestion/transaccion_form_v2.html', 'Nueva Compra')

def venta_create(request):
    return procesar_transaccion(request, TipoOperacion.VENTA, 'Gestion/transaccion_form_v2.html', 'Nueva Venta')

# Deprecated/Redirect old mapping if needed, or remove
def transaccion_create(request):
    return redirect('transaccion-list')
    return render(request, 'Gestion/confirm_delete.html', {'object': entidad, 'cancel_url': 'entidad-list'})

# Transacciones
def transaccion_update(request, pk):
    transaccion = get_object_or_404(CabeceraTransaccion, pk=pk)
    if request.method == 'POST':
        form = CabeceraTransaccionForm(request.POST, instance=transaccion)
        formset = DetalleTransaccionFormSet(request.POST, instance=transaccion)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Transacción actualizada.')
            return redirect('transaccion-list')
    else:
        form = CabeceraTransaccionForm(instance=transaccion)
        formset = DetalleTransaccionFormSet(instance=transaccion)
    return render(request, 'Gestion/transaccion_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Editar Transacción'
    })

def transaccion_detail(request, pk):
    transaccion = get_object_or_404(CabeceraTransaccion, pk=pk)
    return render(request, 'Gestion/transaccion_detail.html', {'transaccion': transaccion, 'title': f'Detalle Transacción #{transaccion.pk}'})
