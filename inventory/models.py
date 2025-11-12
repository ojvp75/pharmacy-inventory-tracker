from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class MedicineInventory(models.Model):
    """Improved inventory model with backward compatibility"""
    STORAGE_CONDITIONS = [
        ('room_temp', 'Room Temperature'),
        ('refrigerated', 'Refrigerated (2-8°C)'),
        ('frozen', 'Frozen (-20°C)'),
        ('controlled_temp', 'Controlled Temperature'),
    ]
    
    # Original fields (maintaining compatibility)
    date = models.DateField()
    medicine_name = models.CharField(max_length=200, db_index=True)
    dosage_form = models.CharField(max_length=100)
    batch_no = models.CharField(max_length=100, db_index=True)
    expiry_date = models.DateField()
    quantity_in = models.PositiveIntegerField(default=0)
    quantity_out = models.PositiveIntegerField(default=0)
    storage_condition = models.CharField(max_length=100, blank=True, choices=STORAGE_CONDITIONS)
    dispensed_to = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    
    # New enhanced fields
    generic_name = models.CharField(max_length=200, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True) 
    strength = models.CharField(max_length=50, blank=True, help_text="e.g., 500mg, 10ml")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supplier_name = models.CharField(max_length=200, blank=True)
    prescribing_doctor = models.CharField(max_length=100, blank=True)
    minimum_stock_level = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['medicine_name']),
            models.Index(fields=['batch_no']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['date']),
        ]

    def clean(self):
        """Custom validation"""
        if self.expiry_date and self.expiry_date <= timezone.now().date():
            raise ValidationError({'expiry_date': 'Expiry date must be in the future'})

    def balance(self):
        """Calculate current balance for this medicine and batch"""
        total_in = MedicineInventory.objects.filter(
            medicine_name=self.medicine_name,
            batch_no=self.batch_no
        ).aggregate(total=models.Sum('quantity_in'))['total'] or 0
        total_out = MedicineInventory.objects.filter(
            medicine_name=self.medicine_name,
            batch_no=self.batch_no
        ).aggregate(total=models.Sum('quantity_out'))['total'] or 0
        return total_in - total_out

    @property
    def is_expired(self):
        """Check if medicine is expired"""
        return self.expiry_date <= timezone.now().date()

    @property
    def days_to_expiry(self):
        """Calculate days until expiry"""
        return (self.expiry_date - timezone.now().date()).days

    @property
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.balance() < self.minimum_stock_level

    def __str__(self):
        return f"{self.medicine_name} ({self.batch_no})"

class Supplier(models.Model):
    """Model to track medicine suppliers"""
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
class StockAlert(models.Model):
    """Model to track stock alerts and notifications"""
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('near_expiry', 'Near Expiry'),
        ('expired', 'Expired'),
    ]
    
    medicine_name = models.CharField(max_length=200)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.medicine_name}"

class DispenseHistory(models.Model):
    """Enhanced dispense history with better tracking"""
    # Legacy fields (keeping original structure)
    date = models.DateTimeField(default=timezone.now)
    medicine_name = models.CharField(max_length=100)
    dosage_form = models.CharField(max_length=100)
    batch_no = models.CharField(max_length=50)
    dispensed_to = models.CharField(max_length=100)
    quantity_out = models.PositiveIntegerField()
    
    # Enhanced fields
    inventory_record = models.ForeignKey(MedicineInventory, on_delete=models.CASCADE, related_name='dispense_records', null=True, blank=True)
    patient_name = models.CharField(max_length=100, blank=True)
    patient_id = models.CharField(max_length=50, blank=True)
    prescribing_doctor = models.CharField(max_length=100, blank=True)
    prescription_number = models.CharField(max_length=100, blank=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dispensed_medicines', null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date']
        
    def __str__(self):
        return f"{self.medicine_name} to {self.dispensed_to} on {self.date.strftime('%Y-%m-%d')}"