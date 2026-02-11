from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.db.models import Sum
from django.utils import timezone
import datetime
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Articulo, Galpon, Lote, RegistroBajas, MovimientoInterno, Entidad, CabeceraTransaccion, RegistroVacunacion, TipoMovimiento, Receta, DetalleTransaccion, TipoOperacion
from .forms import (
    ArticuloForm, GalponForm, LoteForm, RegistroBajasForm, MovimientoInternoForm,
    EntidadForm, CabeceraTransaccionForm, DetalleTransaccionFormSet, RegistroVacunacionForm, RecetaForm,
    CabeceraTransaccionSimpleForm
)
from .utils import get_ordering
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    """Dashboard View"""
    
    total_aves = Lote.objects.filter(estado=True).aggregate(Sum('aves_actuales'))['aves_actuales__sum'] or 0
    # Lote Status Logic
    lotes_activos = Lote.objects.filter(estado=True).count()
    alertas_stock = Articulo.objects.filter(controlar_stock=True, stock_actual__lte=models.F('stock_minimo'))
    
    lotes = Lote.objects.filter(estado=True).order_by('galpon__nombre')
    today =  timezone.localdate()
    
    lotes_status = []
    for lote in lotes:
        # Get ALL feed consumption for today
        consumos_hoy = MovimientoInterno.objects.filter(
            lote=lote, 
            tipo_movimiento=TipoMovimiento.CONSUMO,
            fecha__date=today
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

@login_required
def articulo_list(request):
    query = request.GET.get('q', '')
    tipo_filter = request.GET.get('tipo', '')
    
    articulos = Articulo.objects.all().order_by('nombre')
    
    # Dynamic Filter Options
    available_types = Articulo.objects.values_list('tipo', flat=True).distinct().order_by('tipo')

    # Sorting
    allowed_sort = ['nombre', 'tipo', 'unidad_medida', 'precio_referencia', 'stock_actual', 'stock_minimo']
    ordering = get_ordering(request, allowed_sort, default_field='nombre')
    articulos = articulos.order_by(ordering)


    if query:
        articulos = articulos.filter(nombre__icontains=query)
    
    if tipo_filter:
        articulos = articulos.filter(tipo=tipo_filter)
    
    paginator = Paginator(articulos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'Gestion/articulo_list.html', {
        'articulos': page_obj, 
        'page_obj': page_obj, 
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
        'available_types': available_types
    })

@login_required
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

@login_required
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

@login_required
def articulo_detail(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    return render(request, 'Gestion/articulo_detail.html', {'articulo': articulo, 'title': articulo.nombre})

@login_required
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


@login_required
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

@login_required
def receta_delete(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    producto_pk = receta.producto.pk
    receta.delete()
    messages.success(request, 'Ingrediente eliminado de la receta.')
    return redirect('receta-manage', pk=producto_pk)

# --- GALPONES ---

@login_required
def galpon_list(request):
    galpones = Galpon.objects.all()
    
    # Sorting
    allowed_sort = ['nombre', 'capacidad_max']
    ordering = get_ordering(request, ['nombre', 'capacidad_max', 'pk'], default_field='nombre')
    
    galpones = galpones.order_by(ordering)
    
    return render(request, 'Gestion/galpon_list.html', {'galpones': galpones})

@login_required
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

@login_required
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

@login_required
def galpon_delete(request, pk):
    galpon = get_object_or_404(Galpon, pk=pk)
    if request.method == 'POST':
        galpon.delete()
        messages.success(request, 'Galpón eliminado.')
        return redirect('galpon-list')
    return render(request, 'Gestion/confirm_delete.html', {'object': galpon, 'cancel_url': 'galpon-list'})

# --- BIOLOGICAL CYCLE ---

@login_required
def lote_list(request):
    lotes = Lote.objects.all()

    # Sorting
    allowed_sort = ['galpon__nombre', 'raza', 'aves_iniciales', 'aves_actuales', 'fecha_inicio', 'estado']
    ordering = get_ordering(request, allowed_sort, default_field='-estado') 
    # default was -estado, galpon__nombre. Can't easy support multi-col default with single string helper, 
    # but let's stick to simple sort or modify helper if needed. 
    # Code had .order_by('-estado', 'galpon__nombre').
    
    if not request.GET.get('sort'):
        lotes = lotes.order_by('-estado', 'galpon__nombre')
    else:
        lotes = lotes.order_by(ordering)
        
    return render(request, 'Gestion/lote_list.html', {'lotes': lotes})

@login_required
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

@login_required
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

@login_required
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

@login_required
def lote_overview(request):
    """Macro view of all active lots with last 5 days summary"""
    lotes = Lote.objects.filter(estado=True).order_by('galpon__nombre')
    
    # Range of last 5 days
    today = timezone.localdate()
    dates = [today - timezone.timedelta(days=i) for i in range(5)]
    
    lote_data = []
    
    for lote in lotes:
        daily_stats = []
        for d in dates:
            # Filter movements for this day/lote
            movs = MovimientoInterno.objects.filter(lote=lote, fecha__date=d)
            
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

@login_required
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

@login_required
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

@login_required
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
@login_required
def entidad_list(request):
    query = request.GET.get('q', '')
    rol_filter = request.GET.get('rol', '')
    
    entidades = Entidad.objects.all()

    # Sorting
    allowed_sort = ['nombre_razon_social', 'rut', 'telefono', 'email']
    ordering = get_ordering(request, allowed_sort, default_field='nombre_razon_social')
    entidades = entidades.order_by(ordering)

    
    if query:
        entidades = entidades.filter(
            Q(nombre_razon_social__icontains=query) | 
            Q(rut__icontains=query)
        )
        
    if rol_filter == 'cliente':
        entidades = entidades.filter(es_cliente=True)
    elif rol_filter == 'proveedor':
        entidades = entidades.filter(es_proveedor=True)
        
    paginator = Paginator(entidades, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'Gestion/entidad_list.html', {
        'entidades': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator
    })

@login_required
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

@login_required
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

@login_required
def entidad_detail(request, pk):
    entidad = get_object_or_404(Entidad, pk=pk)
    return render(request, 'Gestion/entidad_detail.html', {'entidad': entidad, 'title': entidad.nombre_razon_social})

@login_required
def transaccion_list(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    tipo_filter = request.GET.get('tipo', '')
    status_filter = request.GET.get('status', '')
    entidad_query = request.GET.get('entidad', '')

    entidad_query = request.GET.get('entidad', '')

    transacciones = CabeceraTransaccion.objects.all()

    
    # Dynamic Filter Options
    available_types = CabeceraTransaccion.objects.values_list('tipo_operacion', flat=True).distinct().order_by('tipo_operacion')
    available_statuses = CabeceraTransaccion.objects.values_list('estado_pago', flat=True).distinct().order_by('estado_pago')

    if start_date:
        transacciones = transacciones.filter(fecha__gte=start_date)
    if end_date:
        transacciones = transacciones.filter(fecha__lte=end_date)
    
    if tipo_filter:
        transacciones = transacciones.filter(tipo_operacion=tipo_filter)
    
    if status_filter:
        transacciones = transacciones.filter(estado_pago=status_filter)
    
    if entidad_query:
        transacciones = transacciones.filter(entidad__nombre_razon_social__icontains=entidad_query)

    # Sorting
    allowed_sort = ['fecha', 'tipo_operacion', 'entidad__nombre_razon_social', 'monto_total', 'estado_pago']
    ordering = get_ordering(request, allowed_sort, default_field='-fecha')
    transacciones = transacciones.order_by(ordering)


    paginator = Paginator(transacciones, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'Gestion/transaccion_list.html', {
        'transacciones': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
        'available_types': available_types,
        'available_statuses': available_statuses
    })

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
                
                # Handle deletions
                for obj in formset.deleted_objects:
                    obj.delete()

                # 3. Update Base Price Logic
                # Iterate over FORMS to access the prefix and POST data
                for f in formset:
                    # Skip if form is not valid or empty or marked for deletion
                    if not f.cleaned_data or f.cleaned_data.get('DELETE'):
                        continue
                    
                    prefix = f.prefix
                    if request.POST.get(f'{prefix}-update_price'):
                        # Access the instance bound to this form
                        detalle = f.instance
                        articulo = detalle.articulo
                        
                        if articulo.precio_referencia != detalle.precio_unitario:
                            old_price = articulo.precio_referencia
                            articulo.precio_referencia = detalle.precio_unitario
                            articulo.save() 
                            
                            # Explicit Log
                            from .signals import create_log_entry
                            create_log_entry(
                                articulo, 'EDICION', 0, 
                                articulo.stock_actual, articulo.stock_actual,
                                f"Precio Base actualizado vía {title}: {old_price} -> {articulo.precio_referencia}"
                            )

                messages.success(request, f'{title} registrada exitosamente.')
                return redirect('transaccion-detail', pk=transaccion.pk)
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

@login_required
def compra_create(request):
    return procesar_transaccion(request, TipoOperacion.COMPRA, 'Gestion/transaccion_form_v2.html', 'Nueva Compra')

@login_required
def venta_create(request):
    return procesar_transaccion(request, TipoOperacion.VENTA, 'Gestion/transaccion_form_v2.html', 'Nueva Venta')

# Deprecated/Redirect old mapping if needed, or remove
@login_required
def transaccion_create(request):
    return redirect('transaccion-list')
    return render(request, 'Gestion/confirm_delete.html', {'object': entidad, 'cancel_url': 'entidad-list'})

# Transacciones
@login_required
def transaccion_update(request, pk):
    transaccion = get_object_or_404(CabeceraTransaccion, pk=pk)
    if request.method == 'POST':
        form = CabeceraTransaccionForm(request.POST, instance=transaccion)
        formset = DetalleTransaccionFormSet(request.POST, instance=transaccion)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Transacción actualizada.')
            return redirect('transaccion-detail', pk=transaccion.pk)
    else:
        form = CabeceraTransaccionForm(instance=transaccion)
        formset = DetalleTransaccionFormSet(instance=transaccion)
    
    # Pass Article Prices for JS
    import json
    precios = {a.id_articulo: str(a.precio_referencia) for a in Articulo.objects.all()}

    return render(request, 'Gestion/transaccion_form_v2.html', {
        'form': form, 
        'formset': formset, 
        'title': f'Editar {transaccion.get_tipo_operacion_display()}',
        'tipo': transaccion.tipo_operacion,
        'precios_json': json.dumps(precios)
    })

@login_required
def transaccion_cambiar_estado(request, pk, nuevo_estado):
    transaccion = get_object_or_404(CabeceraTransaccion, pk=pk)
    
    # 1. Rules:
    # - Cannot change if already ANULADO.
    # - Can go to PAGADO from PENDIENTE.
    # - Can go to ANULADO from PENDIENTE or PAGADO.
    
    if transaccion.estado_pago == 'ANULADO':
        messages.error(request, 'Esta transacción ya está ANULADA y no se puede modificar.')
        return redirect('transaccion-detail', pk=pk)

    if nuevo_estado == 'PAGADO' and transaccion.estado_pago != 'PENDIENTE':
         messages.error(request, 'Solo se puede pagar una transacción Pendiente.')
         return redirect('transaccion-detail', pk=pk)

    try:
        from .models import EstadoPago, TipoOperacion
        from .signals import create_log_entry
        from decimal import Decimal

        if nuevo_estado == 'ANULADO':
            # REVERSE STOCK LOGIC
            is_purchase = transaccion.tipo_operacion == TipoOperacion.COMPRA
            
            for detalle in transaccion.detalles.all():
                articulo = detalle.articulo
                cantidad = detalle.cantidad
                # We need Decimal for calculations
                cantidad_dec = Decimal(str(cantidad))

                # CHECK RECIPE (Only for Sales typically, but check mostly for products)
                # If it's a Sale of a Product with Recipe -> Restore Ingredients
                # If it's a Purchase -> Just remove what was added (Ingredients or Products)
                
                # Logic from signals.py reversed:
                receta = articulo.ingredientes_receta.all()
                has_recipe = receta.exists()

                if not is_purchase and has_recipe:
                    # REVERSE RECIPE SALE: Add back ingredients
                    for ing_receta in receta:
                        ingrediente = ing_receta.ingrediente
                        qty_per_unit = Decimal(str(ing_receta.cantidad))
                        total_restore = cantidad_dec * qty_per_unit
                        
                        if ingrediente.controlar_stock:
                            ingrediente.stock_actual += total_restore
                            ingrediente.save()
                            create_log_entry(
                                ingrediente, 'AJUSTE', total_restore, 
                                ingrediente.stock_actual - total_restore, ingrediente.stock_actual, 
                                f"ANULACIÓN VENTA Pack: {articulo.nombre} (Doc: {transaccion.numero_documento})"
                            )
                else:
                    # STANDARD ITEM (Purchase or Sale without recipe)
                    if articulo.controlar_stock:
                        old_stock = articulo.stock_actual
                        if is_purchase:
                            # Was added, so subtract
                            articulo.stock_actual -= cantidad_dec
                        else:
                            # Was removed, so add
                            articulo.stock_actual += cantidad_dec
                        
                        articulo.save()
                        
                        create_log_entry(
                            articulo, 'AJUSTE', 
                            -cantidad_dec if is_purchase else cantidad_dec,
                            old_stock, articulo.stock_actual,
                            f"ANULACIÓN {transaccion.get_tipo_operacion_display().upper()} #{transaccion.pk}"
                        )

        transaccion.estado_pago = nuevo_estado
        transaccion.save()
        messages.success(request, f'Estado actualizado a {nuevo_estado}. Stock ajustado correctamente.')
        
    except Exception as e:
        messages.error(request, f'Error al actualizar estado: {e}')

    return redirect('transaccion-detail', pk=pk)


@login_required
def transaccion_detail(request, pk):
    transaccion = get_object_or_404(CabeceraTransaccion, pk=pk)
    return render(request, 'Gestion/transaccion_detail.html', {'transaccion': transaccion, 'title': f'Detalle Transacción #{transaccion.pk}'})

@login_required
def transaccion_simple_create(request):
    """Create a 'Simple Purchase' / Expense without item details"""
    if request.method == 'POST':
        form = CabeceraTransaccionSimpleForm(request.POST)
        if form.is_valid():
            transaccion = form.save(commit=False)
            transaccion.tipo_operacion = TipoOperacion.COMPRA
            transaccion.save()
            messages.success(request, 'Gasto/Compra simple registrada exitosamente.')
            return redirect('transaccion-list')
    else:
        form = CabeceraTransaccionSimpleForm(initial={'tipo_operacion': TipoOperacion.COMPRA, 'fecha': timezone.now().date()})
    
    return render(request, 'Gestion/transaccion_simple_form.html', {
        'form': form,
        'title': 'Registrar Gasto / Compra Simple'
    })

@login_required
def auditoria_dashboard(request):
    """General Audit Dashboard: Finance Overview"""
    today = timezone.now().date()
    try:
        month = int(request.GET.get('month', today.month))
    except ValueError:
        month = today.month

    try:
        # Handle cases where year is passed as "2.026" or other formats
        y_str = request.GET.get('year', str(today.year))
        # Remove dots/commas just in case it came from a localized input
        y_clean = y_str.replace('.', '').replace(',', '')
        year = int(y_clean)
    except ValueError:
        year = today.year
    
    # Filter transactions by month/year and NOT Annulled
    transacciones = CabeceraTransaccion.objects.filter(
        fecha__year=year,
        fecha__month=month
    ).exclude(estado_pago='ANULADO').order_by('-fecha')
    transacciones = transacciones.all().order_by('-pk')
    # Aggregates
    ventas = transacciones.filter(tipo_operacion=TipoOperacion.VENTA).aggregate(Sum('monto_total'))['monto_total__sum'] or 0
    compras = transacciones.filter(tipo_operacion=TipoOperacion.COMPRA).aggregate(Sum('monto_total'))['monto_total__sum'] or 0
    balance = ventas - compras
    
    context = {
        'title': 'Auditoría General',
        'transacciones': transacciones,
        'total_ventas': ventas,
        'total_compras': compras,
        'balance': balance,
        'current_month': month,
        'current_year': year,
        'months': range(1, 13),
        'years': range(today.year - 2, today.year + 2),
    }
    return render(request, 'Gestion/auditoria_dashboard.html', context)

@login_required
def salud_dashboard(request):
    """Health & Performance Dashboard"""
    import json
    
    # Filter controls
    periodo_dias = int(request.GET.get('dias', 30))
    lote_id = request.GET.get('lote')
    
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=periodo_dias)
    
    # Get active lotes (or specific one)
    lotes_qs = Lote.objects.filter(estado=True)
    if lote_id:
        selected_lote = get_object_or_404(Lote, pk=lote_id)
        # Keep queryset for dropdown, but filtering logic changes
        target_lotes = [selected_lote]
    else:
        selected_lote = None
        target_lotes = list(lotes_qs)
        
    # Prepare Data Structures
    dates = [start_date + timezone.timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    chart_labels = [d.strftime("%d/%m") for d in dates]
    
    datasets_puesta = []
    datasets_consumo = []
    datasets_mortalidad = []
    datasets_fcr = [] # Feed Conversion Ratio proxy
    
    colores = [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)'
    ]
    
    for idx, lote in enumerate(target_lotes):
        data_puesta = []
        data_consumo = []
        data_mortalidad = []
        data_fcr = []
        
        # Pre-fetch all relevant data to minimize queries in loop
        movs = MovimientoInterno.objects.filter(lote=lote, fecha__date__range=[start_date, end_date])
        bajas = RegistroBajas.objects.filter(lote=lote, fecha__date__lte=end_date) 
        
        current_color = colores[idx % len(colores)]
        
        for d in dates:
            # 1. Birds Alive Calculation
            bajas_acum = bajas.filter(fecha__date__lte=d).aggregate(total=Sum('cantidad'))['total'] or 0
            aves_vivas = lote.aves_iniciales - bajas_acum
            if aves_vivas <= 0: aves_vivas = 1 
                
            # 2. Daily Production & Consumption
            daily_prod = movs.filter(fecha__date=d, tipo_movimiento=TipoMovimiento.PRODUCCION).aggregate(t=Sum('cantidad'))['t'] or 0
            daily_cons = movs.filter(fecha__date=d, tipo_movimiento=TipoMovimiento.CONSUMO).aggregate(t=Sum('cantidad'))['t'] or 0
            daily_fallecidos = bajas.filter(fecha__date=d).aggregate(t=Sum('cantidad'))['t'] or 0
            
            # 3. Metrics
            tasa_puesta = float(daily_prod / aves_vivas) * 100
            consumo_ave = float(daily_cons / aves_vivas) * 1000 
            
            # Efficiency: Grams of feed per egg
            if daily_prod > 0:
                g_per_egg = (float(daily_cons) * 1000) / float(daily_prod)
            else:
                g_per_egg = 0
            
            data_puesta.append(round(tasa_puesta, 1))
            data_consumo.append(round(consumo_ave, 1))
            data_mortalidad.append(int(daily_fallecidos))
            data_fcr.append(round(g_per_egg, 1))

        datasets_puesta.append({
            'label': f"{lote.galpon.nombre} ({lote.raza})",
            'data': data_puesta,
            'borderColor': current_color,
            'tension': 0.3,
            'fill': False
        })
        
        datasets_consumo.append({
            'label': f"{lote.galpon.nombre}",
            'data': data_consumo,
            'borderColor': current_color,
            'borderDash': [5, 5],
            'tension': 0.3,
            'fill': False
        })
        
        datasets_fcr.append({
            'label': f"Eficiencia {lote.galpon.nombre}",
            'data': data_fcr,
            'borderColor': current_color,
            'backgroundColor': current_color.replace('1)', '0.1)'), # Transparent fill
            'tension': 0.4, # Smooth curves
            'fill': True # Area chart
        })

    context = {
        'lotes': lotes_qs,
        'selected_lote': selected_lote,
        'periodo': periodo_dias,
        'chart_labels': json.dumps(chart_labels),
        'datasets_puesta': json.dumps(datasets_puesta),
        'datasets_consumo': json.dumps(datasets_consumo),
        'datasets_fcr': json.dumps(datasets_fcr),
    }

    return render(request, 'Gestion/salud_dashboard.html', context)
