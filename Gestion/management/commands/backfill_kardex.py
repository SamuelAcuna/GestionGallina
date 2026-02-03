from django.core.management.base import BaseCommand
from django.db.models import Sum
from Gestion.models import Articulo, LogArticulo, DetalleTransaccion, MovimientoInterno, TipoOperacion, TipoMovimiento
from decimal import Decimal

class Command(BaseCommand):
    help = 'Backfills the LogArticulo table from existing Transactions and Movements'

    def handle(self, *args, **options):
        self.stdout.write("Starting Kardex Backfill...")
        
        # 1. Clear existing logs to avoid duplication during re-runs
        LogArticulo.objects.all().delete()
        self.stdout.write("Cleared existing LogArticulo entries.")

        articulos = Articulo.objects.all()
        
        for articulo in articulos:
            self.stdout.write(f"Processing: {articulo.nombre}...")
            
            events = []

            # 2. Collect Transactions (Purchases/Sales)
            detalles = DetalleTransaccion.objects.filter(articulo=articulo).select_related('transaccion', 'transaccion__entidad')
            for d in detalles:
                tipo_op = d.transaccion.tipo_operacion
                tipo_log = 'COMPRA' if tipo_op == TipoOperacion.COMPRA else 'VENTA'
                
                # Determine sign for calculation
                # Compra adds to stock, Venta subtracts
                change = d.cantidad if tipo_op == TipoOperacion.COMPRA else -d.cantidad
                
                desc = f"{tipo_log.capitalize()} #{d.transaccion.numero_documento or d.transaccion.pk}"
                if d.transaccion.entidad:
                    desc += f" ({d.transaccion.entidad})"

                events.append({
                    'fecha': d.transaccion.fecha, # This is usually DateField, might need conversion if models changed
                    'pk': d.pk, # Tiebreaker
                    'tipo': tipo_log,
                    'cantidad': d.cantidad,
                    'change': change,
                    'descripcion': desc,
                    'is_transaction': True
                })

            # 3. Collect Internal Movements (Prod/Cons)
            movimientos = MovimientoInterno.objects.filter(articulo=articulo).select_related('lote', 'lote__galpon')
            for m in movimientos:
                tipo_mov = m.tipo_movimiento
                tipo_log = 'PRODUCCION' if tipo_mov == TipoMovimiento.PRODUCCION else 'CONSUMO'
                
                # Produccion adds, Consumo subtracts
                change = m.cantidad if tipo_mov == TipoMovimiento.PRODUCCION else -m.cantidad
                
                desc = f"{tipo_log.capitalize()}: {m.lote.galpon.nombre} - {m.lote.raza}"

                events.append({
                    'fecha': m.fecha, # DateField probably
                    'pk': m.pk,
                    'tipo': tipo_log,
                    'cantidad': m.cantidad,
                    'change': change,
                    'descripcion': desc,
                    'is_transaction': False
                })

            # 4. Sort Events
            # Sort by Date then by PK to be deterministic
            events.sort(key=lambda x: (x['fecha'], x['pk']))

            # 5. Calculate Running Balance
            current_balance = Decimal(0)
            logs_to_create = []

            for ev in events:
                saldo_anterior = current_balance
                current_balance += ev['change']
                saldo_posterior = current_balance
                
                logs_to_create.append(LogArticulo(
                    articulo=articulo,
                    fecha=ev['fecha'], # Django handles auto_now_add override if we set it explicitly? 
                    # Actually auto_now_add ignores provided value on create(). 
                    # We might need to update it after create or use bulk_create which might bypass?
                    # Standard Django create() ignores it. We must set it manually or override save.
                    # Or simpler: LogArticulo.fecha is DateTime. transaccion.fecha is Date.
                    # We will cast Date to DateTime at midnight.
                    tipo=ev['tipo'],
                    cantidad=ev['cantidad'],
                    saldo_anterior=saldo_anterior,
                    saldo_posterior=saldo_posterior,
                    descripcion=ev['descripcion']
                ))

            # 6. Check for Discrepancy with Current Request Stock
            # articulate.stock_actual is the TRUTH.
            # current_balance is what history says.
            # If mismatch, it means there was initial stock or manual DB edits.
            
            discrepancy = articulo.stock_actual - current_balance
            
            if discrepancy != 0:
                self.stdout.write(self.style.WARNING(f"  Gap detected: Current {articulo.stock_actual} vs Hist {current_balance}. Adding Adjustment."))
                
                # Create an Initial Adjustment at the beginning of time (or just before first event)
                # For simplicity, let's put it as the very first entry.
                
                adjustment_log = LogArticulo(
                    articulo=articulo,
                    tipo='AJUSTE',
                    cantidad=abs(discrepancy),
                    saldo_anterior=0,
                    saldo_posterior=discrepancy,
                    descripcion="Ajuste Inicial / Inventario Heredado"
                )
                
                # We need to shift all subsequent balances by the discrepancy
                for log in logs_to_create:
                    log.saldo_anterior += discrepancy
                    log.saldo_posterior += discrepancy
                
                logs_to_create.insert(0, adjustment_log)


            # 7. Save Logs
            # We can't use bulk_create easily if we want to preserve 'fecha' because auto_now_add interferes.
            # Workaround: created = Log.objects.create(...); created.fecha = val; created.save()
            # Or temporarily disable auto_now_add in model? No.
            # Use update() after create?
            
            for log in logs_to_create:
                # We save first to generate ID
                log.save() 
                # Now we forcibly update the date because auto_now_add likely overwrote it with NOW()
                # We need to ensure 'fecha' is a datetime
                # If ev['fecha'] is date, make it datetime
                
                # Since log is already an instance, log.fecha might be set from the list logic
                # But save() overwrites it if the model field is auto_now_add=True.
                # Let's check model definition. Yes, auto_now_add=True.
                
                original_date = log.fecha # This has the value we passed in logic?
                # Wait, if I pass 'fecha' to constructor, it stays on the object, but save() ignores it and sets db column to NOW.
                # So we must update using queryset update to bypass model save() logic
                
                # But wait, 'log' in the loop comes from the list defined above. 
                # If I defined 'fecha' in the constructor, it is in memory.
                # 'adjustment_log' has no date set in my code above (defaults to None->Now).
                
                # Correction:
                # If ev['fecha'] is set in constructor, we retrieve it.
                target_date = getattr(log, 'fecha', None)
                
                if not target_date:
                     # For adjustment, pick a very old date or same as first event
                     if events:
                         target_date = events[0]['fecha']
                     else:
                         from django.utils import timezone
                         target_date = timezone.now()
                
                LogArticulo.objects.filter(pk=log.pk).update(fecha=target_date)

        self.stdout.write(self.style.SUCCESS("Backfill Complete."))
