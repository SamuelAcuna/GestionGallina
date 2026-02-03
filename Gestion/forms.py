from django import forms
from .models import (
    Articulo, Galpon, Lote, RegistroBajas,
    MovimientoInterno, Entidad, CabeceraTransaccion, DetalleTransaccion,
    RegistroVacunacion, Receta
)
from django.forms import inlineformset_factory

class ArticuloForm(forms.ModelForm):
    class Meta:
        model = Articulo
        fields = ['nombre', 'tipo', 'unidad_medida', 'stock_actual', 'stock_minimo', 'precio_referencia', 'controlar_stock', 'es_insumo_receta']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'title': 'Modificar solo mediante transacciones o movimientos'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_referencia': forms.NumberInput(attrs={'class': 'form-control'}),
            'controlar_stock': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_insumo_receta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['ingrediente', 'cantidad']
        widgets = {
            'ingrediente': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }

class GalponForm(forms.ModelForm):
    class Meta:
        model = Galpon
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'capacidad_max': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        exclude = ['aves_actuales', 'fecha_proxima_vacuna'] # proxima_vacuna handled via Vaccination Form
        widgets = {
            'galpon': forms.Select(attrs={'class': 'form-select'}),
            'raza': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'aves_iniciales': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class RegistroBajasForm(forms.ModelForm):
    class Meta:
        model = RegistroBajas
        fields = '__all__'
        widgets = {
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo': forms.Select(attrs={'class': 'form-select'}),
        }

class MovimientoInternoForm(forms.ModelForm):
    class Meta:
        model = MovimientoInterno
        fields = '__all__'
        widgets = {
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'articulo': forms.Select(attrs={'class': 'form-select'}),
            'tipo_movimiento': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class RegistroVacunacionForm(forms.ModelForm):
    class Meta:
        model = RegistroVacunacion
        fields = '__all__'
        widgets = {
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'nombre_vacuna': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proxima_fecha_sugerida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class EntidadForm(forms.ModelForm):
    class Meta:
        model = Entidad
        fields = '__all__'
        widgets = {
            'nombre_razon_social': forms.TextInput(attrs={'class': 'form-control'}),
            'rut': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'es_cliente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_proveedor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CabeceraTransaccionForm(forms.ModelForm):
    class Meta:
        model = CabeceraTransaccion
        exclude = ['monto_total'] # Calculated
        widgets = {
            'tipo_operacion': forms.Select(attrs={'class': 'form-select'}),
            'entidad': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'estado_pago': forms.Select(attrs={'class': 'form-select'}),
            'metodo_pago': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DetalleTransaccionForm(forms.ModelForm):
    class Meta:
        model = DetalleTransaccion
        fields = ['articulo', 'cantidad', 'precio_unitario']
        widgets = {
            'articulo': forms.Select(attrs={'class': 'form-select articulo-select'}), # Class for JS hook
            'cantidad': forms.NumberInput(attrs={'class': 'form-control cantidad-input'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control precio-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add data-price attribute to options
        # This is a bit tricky with standard Django widgets without custom rendering
        # Simpler: We will output a JSON object in the template with {id: price} mapping
        # OR we can iterate choices here if really needed, but template JSON is cleaner.
        # Let's clean up attributes for JS targeting.


DetalleTransaccionFormSet = inlineformset_factory(
    CabeceraTransaccion, DetalleTransaccion,
    form=DetalleTransaccionForm,
    extra=0,
    can_delete=True
)
