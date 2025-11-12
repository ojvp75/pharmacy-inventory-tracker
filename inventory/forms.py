from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import MedicineInventory, Supplier, StockAlert
import datetime

class MedicineInventoryForm(forms.ModelForm):
    """Enhanced form with better validation and widgets"""
    
    class Meta:
        model = MedicineInventory
        exclude = ['created_by', 'created_at', 'updated_at']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'value': timezone.now().date()
            }),
            'medicine_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter medicine name',
                'list': 'medicines'
            }),
            'generic_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Generic/Scientific name'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Manufacturer name'
            }),
            'dosage_form': forms.Select(attrs={'class': 'form-select'}),
            'strength': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 500mg, 10ml'
            }),
            'batch_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Batch/Lot number'
            }),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'quantity_in': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'quantity_out': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'supplier_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Supplier name',
                'list': 'suppliers'
            }),
            'storage_condition': forms.Select(attrs={'class': 'form-select'}),
            'dispensed_to': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Patient name (if dispensing)'
            }),
            'prescribing_doctor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Doctor name'
            }),
            'minimum_stock_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '10'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Additional notes...'
            }),
        }

    # Add custom dosage form choices
    DOSAGE_FORM_CHOICES = [
        ('', 'Select dosage form'),
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('ointment', 'Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('patch', 'Patch'),
        ('suppository', 'Suppository'),
        ('suspension', 'Suspension'),
        ('powder', 'Powder'),
        ('other', 'Other'),
    ]
    
    dosage_form = forms.ChoiceField(
        choices=DOSAGE_FORM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set today's date as default
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()
        
        # Make certain fields required based on context
        if 'quantity_out' in self.data and int(self.data.get('quantity_out', 0)) > 0:
            self.fields['dispensed_to'].required = True

    def clean_expiry_date(self):
        """Validate expiry date"""
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date:
            if expiry_date <= timezone.now().date():
                raise ValidationError("Expiry date must be in the future.")
            if expiry_date <= timezone.now().date() + datetime.timedelta(days=30):
                # Add warning for medicines expiring within 30 days
                pass  # We'll handle this in the view
        return expiry_date

    def clean_batch_no(self):
        """Validate batch number uniqueness for the same medicine"""
        batch_no = self.cleaned_data.get('batch_no')
        medicine_name = self.cleaned_data.get('medicine_name')
        
        if batch_no and medicine_name:
            existing = MedicineInventory.objects.filter(
                medicine_name=medicine_name,
                batch_no=batch_no
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            if existing.exists():
                # Allow multiple entries for same batch (for stock in/out tracking)
                pass
        return batch_no

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        quantity_in = cleaned_data.get('quantity_in', 0)
        quantity_out = cleaned_data.get('quantity_out', 0)
        dispensed_to = cleaned_data.get('dispensed_to', '')

        # Validate that either quantity_in or quantity_out is provided
        if quantity_in == 0 and quantity_out == 0:
            raise ValidationError("Please enter either quantity in or quantity out.")

        # Validate that both are not entered at the same time
        if quantity_in > 0 and quantity_out > 0:
            raise ValidationError("Please enter either quantity in OR quantity out, not both.")

        # If dispensing (quantity_out > 0), require patient name
        if quantity_out > 0 and not dispensed_to:
            raise ValidationError("Patient name is required when dispensing medicine.")

        return cleaned_data

class QuickDispenseForm(forms.Form):
    """Quick form for dispensing medicine"""
    medicine_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Medicine name',
            'list': 'medicines'
        })
    )
    batch_no = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Batch number'
        })
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1'
        })
    )
    patient_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Patient name'
        })
    )
    prescribing_doctor = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prescribing doctor (optional)'
        })
    )

class SupplierForm(forms.ModelForm):
    """Form for adding/editing suppliers"""
    class Meta:
        model = Supplier
        fields = '__all__'
        exclude = ['created_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class StockAlertForm(forms.ModelForm):
    """Form for managing stock alerts"""
    class Meta:
        model = StockAlert
        fields = ['medicine_name', 'alert_type', 'message']
        widgets = {
            'medicine_name': forms.TextInput(attrs={'class': 'form-control'}),
            'alert_type': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }