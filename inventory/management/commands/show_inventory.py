from django.core.management.base import BaseCommand
from inventory.models import MedicineInventory, Supplier
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Show inventory statistics and recent imports'

    def handle(self, *args, **options):
        # Get counts
        total_medicines = MedicineInventory.objects.count()
        total_suppliers = Supplier.objects.count()
        total_users = User.objects.count()
        
        self.stdout.write(f"=== PHARMACY INVENTORY STATISTICS ===")
        self.stdout.write(f"Total Medicine Records: {total_medicines}")
        self.stdout.write(f"Total Suppliers: {total_suppliers}")
        self.stdout.write(f"Total Users: {total_users}")
        
        if total_medicines > 0:
            self.stdout.write(f"\n=== RECENT MEDICINE IMPORTS ===")
            recent_medicines = MedicineInventory.objects.order_by('-created_at')[:10]
            
            for i, med in enumerate(recent_medicines, 1):
                self.stdout.write(f"{i}. {med.medicine_name}")
                self.stdout.write(f"   Batch: {med.batch_no}")
                self.stdout.write(f"   Dosage: {med.dosage_form}")
                self.stdout.write(f"   Expires: {med.expiry_date}")
                self.stdout.write(f"   Qty In: {med.quantity_in} | Qty Out: {med.quantity_out}")
                self.stdout.write(f"   Supplier: {med.supplier_name}")
                self.stdout.write(f"   Added: {med.created_at}")
                self.stdout.write("")
                
        # Show unique medicine names
        unique_medicines = MedicineInventory.objects.values_list('medicine_name', flat=True).distinct()
        self.stdout.write(f"=== UNIQUE MEDICINES ({len(unique_medicines)}) ===")
        for medicine in unique_medicines:
            self.stdout.write(f"- {medicine}")