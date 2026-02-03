from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.db.models import F
from .models import (
    DetalleTransaccion, CabeceraTransaccion, TipoOperacion,
    MovimientoInterno, TipoMovimiento,
    RegistroBajas, Lote,
    Articulo, LogArticulo
)

def create_log_entry(articulo, tipo, cantidad, saldo_ant, saldo_post, descripcion):
    """Helper to create log entry"""
    LogArticulo.objects.create(
        articulo=articulo,
        tipo=tipo,
        cantidad=cantidad,
        saldo_anterior=saldo_ant,
        saldo_posterior=saldo_post,
        descripcion=descripcion
    )

# --- STOCK AUTOMATION ---

@receiver(post_save, sender=DetalleTransaccion)
def update_stock_transaction(sender, instance, created, **kwargs):
    """
    Updates stock based on purchase/sale details.
    Only if controls_stock is True for the article.
    """
    if not created:
        return # For now simplify, handle updates later if needed

    articulo = instance.articulo
    if not articulo.controlar_stock:
        return

    transaccion = instance.transaccion
    
    # Update Transaction Total
    transaccion.monto_total = transaccion.monto_total + instance.subtotal
    transaccion.save(update_fields=['monto_total'])

    stock_inicial = articulo.stock_actual

    # Update Stock
    if transaccion.tipo_operacion == TipoOperacion.COMPRA:
        articulo.stock_actual = F('stock_actual') + instance.cantidad
        articulo.save()
        
        # Log Purchase
        articulo.refresh_from_db()
        create_log_entry(
            articulo, 'COMPRA', instance.cantidad, 
            stock_inicial, articulo.stock_actual, 
            f"Compra a {transaccion.entidad} (Doc: {transaccion.numero_documento})"
        )
        
    elif transaccion.tipo_operacion == TipoOperacion.VENTA:
        # Check if this article has a recipe
        receta = articulo.ingredientes_receta.all()

        if receta.exists():
            # Log the Pack Sale event
            create_log_entry(
                articulo, 'VENTA', instance.cantidad, 
                stock_inicial, stock_inicial, 
                f"Venta Pack a {transaccion.entidad} (Doc: {transaccion.numero_documento})"
            )

            # Deduct ingredients
            for ingrediente_receta in receta:
                ingrediente = ingrediente_receta.ingrediente
                
                # Fix: Cast float to Decimal for multiplication
                from decimal import Decimal
                cantidad_receta = Decimal(str(ingrediente_receta.cantidad))
                cantidad_a_descontar = instance.cantidad * cantidad_receta
                
                if ingrediente.controlar_stock:
                    ing_stock_inicial = ingrediente.stock_actual
                    ingrediente.stock_actual = F('stock_actual') - cantidad_a_descontar
                    ingrediente.save()
                    
                    ingrediente.refresh_from_db()
                    # Using 'VENTA' for ingredients too, so it's clear it left via a sale
                    create_log_entry(
                        ingrediente, 'VENTA', cantidad_a_descontar,
                        ing_stock_inicial, ingrediente.stock_actual,
                        f"Venta en Pack: {articulo.nombre} (Doc: {transaccion.numero_documento})"
                    )

        else:
            # Standard Sale (No recipe)
            articulo.stock_actual = F('stock_actual') - instance.cantidad
            articulo.save()
            
            # Log Sale
            articulo.refresh_from_db()
            create_log_entry(
                articulo, 'VENTA', instance.cantidad,
                stock_inicial, articulo.stock_actual,
                f"Venta a {transaccion.entidad} (Doc: {transaccion.numero_documento})"
            )

@receiver(post_save, sender=MovimientoInterno)
def update_stock_internal(sender, instance, created, **kwargs):
    """
    Updates stock based on internal usage/production.
    """
    if not created:
        return

    articulo = instance.articulo
    if not articulo.controlar_stock:
        return

    stock_inicial = articulo.stock_actual
    
    tipo_log = 'OTRO'
    # More descriptive message for internal movements
    desc = f"{instance.get_tipo_movimiento_display()}: {instance.lote.galpon.nombre} - {instance.lote.raza}"

    if instance.tipo_movimiento == TipoMovimiento.CONSUMO:
        articulo.stock_actual = F('stock_actual') - instance.cantidad
        tipo_log = 'CONSUMO'
    elif instance.tipo_movimiento == TipoMovimiento.PRODUCCION:
        articulo.stock_actual = F('stock_actual') + instance.cantidad
        tipo_log = 'PRODUCCION'
    
    articulo.save()
    
    articulo.refresh_from_db()
    create_log_entry(
        articulo, tipo_log, instance.cantidad,
        stock_inicial, articulo.stock_actual,
        desc
    )

# --- METADATA LOGGING ---

@receiver(pre_save, sender=Articulo)
def log_article_changes(sender, instance, **kwargs):
    """
    Log changes to critical metadata (Min Stock, Name, etc.)
    """
    if instance.pk:
        try:
            old_instance = Articulo.objects.get(pk=instance.pk)
            changes = []
            
            if old_instance.stock_minimo != instance.stock_minimo:
                changes.append(f"Stock Min: {old_instance.stock_minimo} -> {instance.stock_minimo}")
            
            if old_instance.nombre != instance.nombre:
                changes.append(f"Nombre: {old_instance.nombre} -> {instance.nombre}")
                
            if changes:
                # We can't easily get post-save saldo here without double save, 
                # using current stock as "no change" to stock
                create_log_entry(
                    instance, 'EDICION', 0,
                    instance.stock_actual, instance.stock_actual,
                    "; ".join(changes)
                )
        except Articulo.DoesNotExist:
            pass # New article creation

# --- POPULATION AUTOMATION ---

@receiver(post_save, sender=RegistroBajas)
def update_population(sender, instance, created, **kwargs):
    """
    Updates bird population in the Lote.
    """
    if not created:
        return
    
    lote = instance.lote
    lote.aves_actuales = F('aves_actuales') - instance.cantidad
    lote.save()

# --- INTEGRITY RULES ---

@receiver(pre_save, sender=MovimientoInterno)
def validate_batch_status(sender, instance, **kwargs):
    """
    Prevent CONSUMPTION for CLOSED batches.
    """
    if instance.tipo_movimiento == TipoMovimiento.CONSUMO:
        if not instance.lote.estado: # False = CERRADO
            raise ValidationError(f"Cannot register consumption for a CLOSED batch (Lote {instance.lote.id_lote})")

from .models import RegistroVacunacion

@receiver(post_save, sender=RegistroVacunacion)
def update_next_vaccination(sender, instance, created, **kwargs):
    """
    Updates the next vaccination date on the Lote.
    """
    if instance.proxima_fecha_sugerida:
        lote = instance.lote
        lote.fecha_proxima_vacuna = instance.proxima_fecha_sugerida
        lote.save(update_fields=['fecha_proxima_vacuna'])
