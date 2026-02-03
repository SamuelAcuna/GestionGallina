from django.test import TestCase
from django.utils import timezone
from .models import (
    Articulo, TipoArticulo,
    Galpon, Lote, RegistroBajas, MotivoBaja,
    MovimientoInterno, TipoMovimiento,
    Entidad, CabeceraTransaccion, DetalleTransaccion, TipoOperacion, EstadoPago
)
from django.core.exceptions import ValidationError

class GestionTests(TestCase):
    def setUp(self):
        # Create Masters
        self.articulo_insumo = Articulo.objects.create(
            nombre="Alimento",
            tipo=TipoArticulo.INSUMO,
            unidad_medida="kg",
            stock_actual=100,
            controlar_stock=True
        )
        self.articulo_producto = Articulo.objects.create(
            nombre="Huevos",
            tipo=TipoArticulo.PRODUCTO,
            unidad_medida="unidades",
            stock_actual=0,
            controlar_stock=True
        )
        self.galpon = Galpon.objects.create(nombre="Galpon 1", capacidad_max=1000)
        self.lote = Lote.objects.create(
            galpon=self.galpon,
            raza="Raza 1",
            aves_iniciales=100,
            estado=True
        )
        self.entidad = Entidad.objects.create(nombre_razon_social="Proveedor 1", es_proveedor=True)

    def test_stock_update_purchase(self):
        """Test that purchasing increases stock."""
        transaccion = CabeceraTransaccion.objects.create(
            tipo_operacion=TipoOperacion.COMPRA,
            entidad=self.entidad,
            monto_total=0
        )
        DetalleTransaccion.objects.create(
            transaccion=transaccion,
            articulo=self.articulo_insumo,
            cantidad=50,
            precio_unitario=10
        )
        self.articulo_insumo.refresh_from_db()
        self.assertEqual(self.articulo_insumo.stock_actual, 150) # 100 + 50

    def test_stock_update_sale(self):
        """Test that selling decreases stock."""
        # Setup initial stock for product
        self.articulo_producto.stock_actual = 50
        self.articulo_producto.save()

        transaccion = CabeceraTransaccion.objects.create(
            tipo_operacion=TipoOperacion.VENTA,
            entidad=self.entidad,
            monto_total=0
        )
        DetalleTransaccion.objects.create(
            transaccion=transaccion,
            articulo=self.articulo_producto,
            cantidad=20,
            precio_unitario=5
        )
        self.articulo_producto.refresh_from_db()
        self.assertEqual(self.articulo_producto.stock_actual, 30) # 50 - 20

    def test_internal_consumption(self):
        """Test that internal consumption decreases stock."""
        MovimientoInterno.objects.create(
            lote=self.lote,
            articulo=self.articulo_insumo,
            tipo_movimiento=TipoMovimiento.CONSUMO,
            cantidad=10
        )
        self.articulo_insumo.refresh_from_db()
        self.assertEqual(self.articulo_insumo.stock_actual, 90) # 100 - 10

    def test_internal_production(self):
        """Test that production increases stock."""
        MovimientoInterno.objects.create(
            lote=self.lote,
            articulo=self.articulo_producto,
            tipo_movimiento=TipoMovimiento.PRODUCCION,
            cantidad=100
        )
        self.articulo_producto.refresh_from_db()
        self.assertEqual(self.articulo_producto.stock_actual, 100) # 0 + 100

    def test_population_decrease(self):
        """Test that mortality decreases population."""
        RegistroBajas.objects.create(
            lote=self.lote,
            cantidad=5,
            motivo=MotivoBaja.MUERTE_NATURAL
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.aves_actuales, 95) # 100 - 5

    def test_closed_batch_consumption_constraint(self):
        """Test that consuming for a CLOSED batch raises ValidationError."""
        self.lote.estado = False
        self.lote.save()
        
        with self.assertRaises(ValidationError):
            MovimientoInterno.objects.create(
                lote=self.lote,
                articulo=self.articulo_insumo,
                tipo_movimiento=TipoMovimiento.CONSUMO,
                cantidad=10
            )
