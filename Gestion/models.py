from django.db import models
from django.utils import timezone

# --- ENUMS ---

class TipoArticulo(models.TextChoices):
    INSUMO = 'INSUMO', 'Insumo'
    PRODUCTO = 'PRODUCTO', 'Producto'
    SERVICIO = 'SERVICIO', 'Servicio'

class MotivoBaja(models.TextChoices):
    MUERTE_NATURAL = 'MUERTE_NATURAL', 'Muerte Natural'
    ACCIDENTE = 'ACCIDENTE', 'Accidente'
    DESCARTE = 'DESCARTE', 'Descarte'
    DEPREDADOR = 'DEPREDADOR', 'Depredador'

class TipoMovimiento(models.TextChoices):
    CONSUMO = 'CONSUMO', 'Consumo'
    PRODUCCION = 'PRODUCCION', 'Produccion'

class TipoOperacion(models.TextChoices):
    COMPRA = 'COMPRA', 'Compra'
    VENTA = 'VENTA', 'Venta'

class EstadoPago(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    PAGADO = 'PAGADO', 'Pagado'
    ANULADO = 'ANULADO', 'Anulado'

class MetodoPago(models.TextChoices):
    EFECTIVO = 'EFECTIVO', 'Efectivo'
    TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'
    DEBITO = 'DEBITO', 'Débito'
    CREDITO = 'CREDITO', 'Crédito'
    CHEQUE = 'CHEQUE', 'Cheque'
    OTRO = 'OTRO', 'Otro'

# --- INVENTORY & MASTERS ---

class Articulo(models.Model):
    id_articulo = models.AutoField(primary_key=True)
    class UnidadMedida(models.TextChoices):
        UNIDAD = 'Unidad', 'Unidad'
        KG = 'Kg', 'Kg'
        LITRO = 'Litro', 'Litro'

    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TipoArticulo.choices)
    unidad_medida = models.CharField(max_length=50, choices=UnidadMedida.choices, default=UnidadMedida.UNIDAD)
    controlar_stock = models.BooleanField(default=True)
    stock_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_referencia = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Precio base para compras o ventas")
    es_insumo_receta = models.BooleanField(default=False, help_text="Marcar si es un envase o insumo auxiliar para recetas (no se muestra en Kiosco)")

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

class Receta(models.Model):
    """Defines the composition of a 'Pack' product (e.g. Dozen Eggs)"""
    producto = models.ForeignKey(Articulo, on_delete=models.CASCADE, related_name='ingredientes_receta', limit_choices_to={'tipo': 'PRODUCTO'})
    ingrediente = models.ForeignKey(Articulo, on_delete=models.CASCADE, related_name='usado_en_recetas')
    cantidad = models.FloatField(help_text="Cantidad de ingrediente por unidad de producto")

    class Meta:
        unique_together = ('producto', 'ingrediente')

    def __str__(self):
        return f"{self.producto}: {self.cantidad} {self.ingrediente.unidad_medida} de {self.ingrediente}"

class LogArticulo(models.Model):
    """Unified Audit Log for Article History (Kardex)"""
    TIPO_EVENTO = [
        ('VENTA', 'Venta'),
        ('COMPRA', 'Compra'),
        ('PRODUCCION', 'Producción'),
        ('CONSUMO', 'Consumo'),
        ('AJUSTE', 'Ajuste Manual'),
        ('EDICION', 'Edición Metadata'),
    ]
    
    articulo = models.ForeignKey(Articulo, on_delete=models.CASCADE, related_name='logs')
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=TIPO_EVENTO)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Magnitude of change")
    saldo_anterior = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_posterior = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.fecha} - {self.articulo} - {self.tipo}"

class Galpon(models.Model):
    id_galpon = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    capacidad_max = models.IntegerField()

    def __str__(self):
        return self.nombre

# --- BIOLOGICAL CYCLE ---

class Lote(models.Model):
    id_lote = models.AutoField(primary_key=True)
    galpon = models.ForeignKey(Galpon, on_delete=models.CASCADE)
    raza = models.CharField(max_length=100)
    fecha_inicio = models.DateField(default=timezone.now)
    aves_iniciales = models.IntegerField()
    aves_actuales = models.IntegerField(editable=False) # Updated by signal
    estado = models.BooleanField(default=True) # Active=True, Closed=False
    fecha_proxima_vacuna = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and self.aves_actuales is None:
            self.aves_actuales = self.aves_iniciales
        super().save(*args, **kwargs)

    def __str__(self):
        status = "ACTIVO" if self.estado else "CERRADO"
        return f"Lote {self.id_lote} - {self.galpon.nombre} ({status})"

class RegistroVacunacion(models.Model):
    id_vacunacion = models.AutoField(primary_key=True)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    nombre_vacuna = models.CharField(max_length=200)
    fecha = models.DateField(default=timezone.now)
    proxima_fecha_sugerida = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre_vacuna} - {self.lote}"

class RegistroBajas(models.Model):
    id_baja = models.AutoField(primary_key=True)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)
    cantidad = models.IntegerField()
    motivo = models.CharField(
        max_length=20,
        choices=MotivoBaja.choices,
        default=MotivoBaja.MUERTE_NATURAL
    )

    def __str__(self):
        return f"Baja {self.cantidad} en Lote {self.lote.id_lote}"

class MovimientoInterno(models.Model):
    id_movimiento = models.AutoField(primary_key=True)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    articulo = models.ForeignKey(Articulo, on_delete=models.CASCADE)
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TipoMovimiento.choices
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.get_tipo_movimiento_display()} - {self.articulo.nombre}"

# --- COMMERCIAL CYCLE ---

class Entidad(models.Model):
    id_entidad = models.AutoField(primary_key=True)
    nombre_razon_social = models.CharField(max_length=200)
    rut = models.CharField(max_length=20, blank=True, null=True)
    es_cliente = models.BooleanField(default=False)
    es_proveedor = models.BooleanField(default=False)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.CharField(max_length=250, blank=True, null=True)

    def __str__(self):
        roles = []
        if self.es_cliente: roles.append("Cliente")
        if self.es_proveedor: roles.append("Proveedor")
        return f"{self.nombre_razon_social} ({', '.join(roles)})"

class CabeceraTransaccion(models.Model):
    id_transaccion = models.AutoField(primary_key=True)
    tipo_operacion = models.CharField(
        max_length=20,
        choices=TipoOperacion.choices
    )
    entidad = models.ForeignKey(Entidad, on_delete=models.PROTECT)
    fecha = models.DateField(default=timezone.now)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE
    )
    metodo_pago = models.CharField(
        max_length=20, 
        choices=MetodoPago.choices,
        default=MetodoPago.EFECTIVO
    )
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_tipo_operacion_display()} #{self.id_transaccion} - {self.entidad.nombre_razon_social}"

class DetalleTransaccion(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    transaccion = models.ForeignKey(CabeceraTransaccion, on_delete=models.CASCADE, related_name='detalles')
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
        # Verify if we should update transaction total here or via signal/method
    
    def __str__(self):
        return f"{self.articulo.nombre} x {self.cantidad}"
