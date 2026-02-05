from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Gestion.models import *
from django.utils import timezone
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Popula la base de datos con datos de prueba'

    def handle(self, *args, **kwargs):
        self.stdout.write('Iniciando populacion...')

        # 1. Superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS('Superuser "admin" creado (pass: admin)'))

        # 2. Galpones
        galpones = []
        for i in range(1, 4):
            g, _ = Galpon.objects.get_or_create(
                nombre=f"Galpón {i}",
                capacidad_max=1000
            )
            galpones.append(g)
        self.stdout.write(self.style.SUCCESS(f'{len(galpones)} Galpones creados'))

        # 3. Articulos
        # -- Insumos
        alimento_inicio, _ = Articulo.objects.get_or_create(
            nombre="Alimento Inicio",
            defaults={'tipo': TipoArticulo.INSUMO, 'unidad_medida': 'kg', 'stock_minimo': 100, 'precio_referencia': 500, 'controlar_stock': True, 'stock_actual': 0}
        )
        alimento_engorde, _ = Articulo.objects.get_or_create(
            nombre="Alimento Engorde",
            defaults={'tipo': TipoArticulo.INSUMO, 'unidad_medida': 'kg', 'stock_minimo': 100, 'precio_referencia': 450, 'controlar_stock': True, 'stock_actual': 0}
        )
        maiz, _ = Articulo.objects.get_or_create(
            nombre="Maíz",
            defaults={'tipo': TipoArticulo.INSUMO, 'unidad_medida': 'kg', 'stock_minimo': 200, 'precio_referencia': 300, 'controlar_stock': True, 'stock_actual': 0}
        )
        
        # -- Medicinas
        vacuna_newcastle, _ = Articulo.objects.get_or_create(
            nombre="Vacuna Newcastle",
            defaults={'tipo': TipoArticulo.INSUMO, 'unidad_medida': 'dosis', 'stock_minimo': 50, 'precio_referencia': 50, 'controlar_stock': True, 'stock_actual': 0}
        )

        # -- Productos (Huevos)
        huevo_blanco, _ = Articulo.objects.get_or_create(
            nombre="Huevo Blanco (Unidad)",
            defaults={'tipo': TipoArticulo.PRODUCTO, 'unidad_medida': 'un', 'stock_minimo': 100, 'precio_referencia': 150, 'controlar_stock': True, 'stock_actual': 0}
        )
        huevo_color, _ = Articulo.objects.get_or_create(
            nombre="Huevo Color (Unidad)",
            defaults={'tipo': TipoArticulo.PRODUCTO, 'unidad_medida': 'un', 'stock_minimo': 100, 'precio_referencia': 180, 'controlar_stock': True, 'stock_actual': 0}
        )

        # -- Packs
        caja_huevos, _ = Articulo.objects.get_or_create(
            nombre="Bandeja 30 Huevos",
            defaults={'tipo': TipoArticulo.PRODUCTO, 'unidad_medida': 'un', 'stock_minimo': 10, 'precio_referencia': 4000, 'controlar_stock': False}
        )
        # Receta Caja
        Receta.objects.get_or_create(producto=caja_huevos, ingrediente=huevo_blanco, defaults={'cantidad': 30})
        
        self.stdout.write(self.style.SUCCESS('Artículos creados'))

        # 4. Entidades
        prov_alim, _ = Entidad.objects.get_or_create(
            nombre_razon_social="Alimentos del Sur SA",
            defaults={'rut': '76.123.456-7', 'es_proveedor': True}
        )
        prov_vet, _ = Entidad.objects.get_or_create(
            nombre_razon_social="Veterinaria Central",
            defaults={'rut': '88.999.111-K', 'es_proveedor': True}
        )
        cliente_juan, _ = Entidad.objects.get_or_create(
            nombre_razon_social="Almacén Don Juan",
            defaults={'rut': '12.345.678-9', 'es_cliente': True, 'telefono': '+56912341234'}
        )
        self.stdout.write(self.style.SUCCESS('Entidades creadas'))

        # 5. Lotes
        lote1, _ = Lote.objects.get_or_create(
            galpon=galpones[0],
            raza='Hy-Line Brown',
            defaults={
                'fecha_inicio': timezone.now().date() - timedelta(days=30),
                'aves_iniciales': 500,
                'aves_actuales': 495,
                'estado': True
            }
        )
        lote2, _ = Lote.objects.get_or_create(
            galpon=galpones[1],
            raza='Lohmann White',
            defaults={
                'fecha_inicio': timezone.now().date() - timedelta(days=2),
                'aves_iniciales': 300,
                'aves_actuales': 300,
                'estado': True
            }
        )
        self.stdout.write(self.style.SUCCESS('Lotes creados'))

        # 6. Transacciones (Compras para Stock)
        # Compra Alimento
        compra1 = CabeceraTransaccion.objects.create(
            tipo_operacion=TipoOperacion.COMPRA,
            entidad=prov_alim,
            fecha=timezone.now().date() - timedelta(days=10),
            numero_documento="FACT-1001",
            estado_pago=EstadoPago.PAGADO,
            metodo_pago=MetodoPago.TRANSFERENCIA
        )
        DetalleTransaccion.objects.create(transaccion=compra1, articulo=alimento_inicio, cantidad=1000, precio_unitario=480) # 480k
        DetalleTransaccion.objects.create(transaccion=compra1, articulo=maiz, cantidad=500, precio_unitario=290) # 145k
        # Total gets updated by signal usually, but let's ensure
        compra1.monto_total = (1000*480) + (500*290)
        compra1.save()
        
        # Ensure Stock (Signal handles it? Yes, we rely on signal for COMPRA)
        # But signals might not trigger on create if not careful, let's refresh stock manually just in case or trust logic.
        # My signals use POST_SAVE.
        
        # Compra Vacunas
        compra2 = CabeceraTransaccion.objects.create(
            tipo_operacion=TipoOperacion.COMPRA,
            entidad=prov_vet,
            fecha=timezone.now().date() - timedelta(days=5),
            numero_documento="BOL-555",
            estado_pago=EstadoPago.PAGADO
        )
        DetalleTransaccion.objects.create(transaccion=compra2, articulo=vacuna_newcastle, cantidad=200, precio_unitario=60000) # Expensive? maybe 60/dose
        # Let's fix price
        DetalleTransaccion.objects.filter(articulo=vacuna_newcastle).update(precio_unitario=60)
        compra2.monto_total = 200 * 60
        compra2.save()

        # Produccion (Huevos) -> Add Stock manually via MovimientoInterno logic
        # OR just mock stock
        huevo_blanco.stock_actual = 5000
        huevo_blanco.save()
        huevo_color.stock_actual = 3000
        huevo_color.save()

        # Ventas
        venta1 = CabeceraTransaccion.objects.create(
            tipo_operacion=TipoOperacion.VENTA,
            entidad=cliente_juan,
            fecha=timezone.now().date(),
            numero_documento="BOL-001",
            estado_pago=EstadoPago.PAGADO,
            metodo_pago=MetodoPago.EFECTIVO
        )
        DetalleTransaccion.objects.create(transaccion=venta1, articulo=huevo_blanco, cantidad=100, precio_unitario=180)
        venta1.monto_total = 100 * 180
        venta1.save()

        # Gastos Simples
        gasto1 = CabeceraTransaccion.objects.create(
            tipo_operacion=TipoOperacion.COMPRA,
            entidad=prov_vet,
            fecha=timezone.now().date() - timedelta(days=1),
            monto_total=15000,
            estado_pago=EstadoPago.PAGADO,
            observaciones="Compra de guantes y mascarillas",
            metodo_pago=MetodoPago.EFECTIVO
        )

        # 7. Movimientos Internos (Daily Farming Logic)
        # We need Consumo (Feed) and Produccion (Eggs)
        
        # Helper logs
        fechas_movs = [timezone.now().date() - timedelta(days=i) for i in range(5)] # Last 5 days
        
        for d in fechas_movs:
            # Lote 1 (Hy-Line): Produces Brown Eggs, Eats Alimento Inicio (or Engorde)
            # Produccion ~90% -> 495 birds * 0.9 = 445 eggs
            MovimientoInterno.objects.create(
                lote=lote1,
                articulo=huevo_color,
                tipo_movimiento=TipoMovimiento.PRODUCCION,
                cantidad=445,
                fecha=d
            )
            # Consumo ~110g/bird -> 495 * 0.11 = 54.45 kg
            MovimientoInterno.objects.create(
                lote=lote1,
                articulo=alimento_inicio,
                tipo_movimiento=TipoMovimiento.CONSUMO,
                cantidad=54.45,
                fecha=d
            )
            
            # Lote 2 (White): Produces White Eggs
            # Produccion ~95% -> 300 * 0.95 = 285 eggs
            MovimientoInterno.objects.create(
                lote=lote2,
                articulo=huevo_blanco,
                tipo_movimiento=TipoMovimiento.PRODUCCION,
                cantidad=285,
                fecha=d
            )
            # Consumo
            MovimientoInterno.objects.create(
                lote=lote2,
                articulo=alimento_inicio,
                tipo_movimiento=TipoMovimiento.CONSUMO,
                cantidad=33.0,
                fecha=d
            )

        self.stdout.write(self.style.SUCCESS('Movimientos Internos (Produccion/Consumo) creados'))
        self.stdout.write(self.style.SUCCESS('Transacciones de prueba creadas'))
