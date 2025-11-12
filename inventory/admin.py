from django.contrib import admin
from django.utils import timezone
from .models import MedicineInventory, Supplier, StockAlert, DispenseHistory

@admin.register(MedicineInventory)
class MedicineInventoryAdmin(admin.ModelAdmin):
    list_display = ['medicine_name', 'batch_no', 'quantity_in', 'quantity_out', 'balance', 'expiry_date', 'is_expired', 'created_by']
    list_filter = ['dosage_form', 'storage_condition', 'expiry_date', 'created_at']
    search_fields = ['medicine_name', 'batch_no', 'generic_name', 'manufacturer']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at', 'balance', 'is_expired', 'days_to_expiry']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('medicine_name', 'generic_name', 'dosage_form', 'strength', 'manufacturer')
        }),
        ('Batch Details', {
            'fields': ('batch_no', 'expiry_date', 'supplier_name', 'storage_condition')
        }),
        ('Quantity & Cost', {
            'fields': ('quantity_in', 'quantity_out', 'unit_cost', 'minimum_stock_level')
        }),
        ('Dispensing Info', {
            'fields': ('dispensed_to', 'prescribing_doctor')
        }),
        ('Additional Info', {
            'fields': ('date', 'notes', 'created_by')
        }),
        ('System Fields', {
            'fields': ('created_at', 'updated_at', 'balance', 'is_expired', 'days_to_expiry'),
            'classes': ('collapse',)
        })
    )

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'created_at']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    readonly_fields = ['created_at']

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['medicine_name', 'alert_type', 'is_acknowledged', 'created_at', 'acknowledged_by']
    list_filter = ['alert_type', 'is_acknowledged', 'created_at']
    search_fields = ['medicine_name', 'message']
    readonly_fields = ['created_at', 'acknowledged_at']
    
    actions = ['mark_acknowledged']
    
    def mark_acknowledged(self, request, queryset):
        queryset.update(is_acknowledged=True, acknowledged_by=request.user, acknowledged_at=timezone.now())
        self.message_user(request, f"Marked {queryset.count()} alerts as acknowledged.")
    mark_acknowledged.short_description = "Mark selected alerts as acknowledged"

@admin.register(DispenseHistory)
class DispenseHistoryAdmin(admin.ModelAdmin):
    list_display = ['medicine_name', 'dispensed_to', 'quantity_out', 'date', 'dispensed_by']
    list_filter = ['date', 'dosage_form']
    search_fields = ['medicine_name', 'dispensed_to', 'patient_name', 'prescription_number']
    date_hierarchy = 'date'
    readonly_fields = ['date'] if 'date' in [f.name for f in DispenseHistory._meta.fields] else []
