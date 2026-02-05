import os
import django
from django.utils import timezone
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GestionGallina.settings')
django.setup()

from Gestion.models import MovimientoInterno, TipoMovimiento, Lote

print(f"Current Timezone Now: {timezone.now()}")
print(f"Current Date: {timezone.now().date()}")

print("\n--- LAST 10 INTERNAL MOVEMENTS ---")
movs = MovimientoInterno.objects.all().order_by('-fecha')[:10]
for m in movs:
    print(f"ID: {m.pk} | Date: {m.fecha} | Type: {m.tipo_movimiento} | Lote: {m.lote} | Qty: {m.cantidad}")

print("\n--- CHECKING TODAY'S KIOSK QUERY ---")
today = timezone.now().date()
qs = MovimientoInterno.objects.filter(fecha__date=today)
print(f"Querying fecha__date={today}")
print(f"Count: {qs.count()}")
for m in qs:
     print(f"MATCH: ID {m.pk} | {m.fecha}")
