from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json
import csv
from datetime import datetime, timedelta

from .models import MedicineInventory, DispenseHistory, Supplier, StockAlert
from .forms import MedicineInventoryForm, QuickDispenseForm, SupplierForm

@login_required
def inventory_list(request):
    """Enhanced inventory list with filtering, sorting, and pagination"""
    inventory_list = MedicineInventory.objects.select_related('created_by')
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        inventory_list = inventory_list.filter(
            Q(medicine_name__icontains=query) | 
            Q(batch_no__icontains=query) |
            Q(generic_name__icontains=query) |
            Q(manufacturer__icontains=query)
        )
    
    # Filter by dosage form
    dosage_form = request.GET.get('dosage_form')
    if dosage_form:
        inventory_list = inventory_list.filter(dosage_form=dosage_form)
    
    # Filter by expiry status
    expiry_filter = request.GET.get('expiry')
    if expiry_filter == 'expired':
        inventory_list = inventory_list.filter(expiry_date__lte=timezone.now().date())
    elif expiry_filter == 'expiring_soon':
        next_month = timezone.now().date() + timedelta(days=30)
        inventory_list = inventory_list.filter(
            expiry_date__gt=timezone.now().date(),
            expiry_date__lte=next_month
        )
    
    # Filter by stock level
    stock_filter = request.GET.get('stock')
    low_stock_items = []
    if stock_filter == 'low':
        # Get items with low stock
        for item in inventory_list:
            if item.is_low_stock:
                low_stock_items.append(item.id)
        inventory_list = inventory_list.filter(id__in=low_stock_items)
    
    # Sorting
    sort_by = request.GET.get('sort', '-date')
    valid_sorts = ['medicine_name', '-medicine_name', 'expiry_date', '-expiry_date', 'date', '-date']
    if sort_by in valid_sorts:
        inventory_list = inventory_list.order_by(sort_by)
    
    # Get unique dosage forms for filter
    dosage_forms = MedicineInventory.objects.values_list('dosage_form', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(inventory_list, 25)  # Show 25 items per page
    page = request.GET.get('page')
    
    try:
        inventory = paginator.page(page)
    except PageNotAnInteger:
        inventory = paginator.page(1)
    except EmptyPage:
        inventory = paginator.page(paginator.num_pages)
    
    # Quick stats
    total_medicines = MedicineInventory.objects.values('medicine_name').distinct().count()
    expired_count = MedicineInventory.objects.filter(expiry_date__lte=timezone.now().date()).count()
    
    context = {
        'inventory': inventory,
        'query': query,
        'dosage_forms': dosage_forms,
        'selected_dosage_form': dosage_form,
        'selected_expiry_filter': expiry_filter,
        'selected_stock_filter': stock_filter,
        'sort_by': sort_by,
        'total_medicines': total_medicines,
        'expired_count': expired_count,
    }
    
    return render(request, 'inventory_list.html', context)

@login_required
def add_inventory(request):
    """Enhanced add inventory with better validation and messages"""
    if request.method == 'POST':
        form = MedicineInventoryForm(request.POST)
        if form.is_valid():
            inventory = form.save(commit=False)
            inventory.created_by = request.user
            inventory.save()
            
            # Create dispense history if quantity_out > 0
            if inventory.quantity_out > 0:
                DispenseHistory.objects.create(
                    medicine_name=inventory.medicine_name,
                    dosage_form=inventory.dosage_form,
                    batch_no=inventory.batch_no,
                    dispensed_to=inventory.dispensed_to,
                    quantity_out=inventory.quantity_out,
                    dispensed_by=request.user,
                    inventory_record=inventory
                )
                messages.success(request, f'Medicine "{inventory.medicine_name}" dispensed successfully.')
            else:
                messages.success(request, f'Medicine "{inventory.medicine_name}" added to inventory successfully.')
            
            # Check for low stock alerts
            if inventory.is_low_stock:
                StockAlert.objects.get_or_create(
                    medicine_name=inventory.medicine_name,
                    alert_type='low_stock',
                    defaults={'message': f'Stock is running low for {inventory.medicine_name}'}
                )
            
            return redirect('inventory_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MedicineInventoryForm()
    
    # Get suppliers and medicines for autocomplete
    suppliers = Supplier.objects.all()
    medicines = MedicineInventory.objects.values_list('medicine_name', flat=True).distinct()
    
    context = {
        'form': form,
        'suppliers': suppliers,
        'medicines': medicines,
        'title': 'Add Medicine to Inventory'
    }
    return render(request, 'inventory_form.html', context)

@login_required
def edit_inventory(request, pk):
    """Enhanced edit inventory"""
    item = get_object_or_404(MedicineInventory, pk=pk)
    
    if request.method == 'POST':
        form = MedicineInventoryForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Medicine "{item.medicine_name}" updated successfully.')
            return redirect('inventory_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MedicineInventoryForm(instance=item)
    
    suppliers = Supplier.objects.all()
    medicines = MedicineInventory.objects.values_list('medicine_name', flat=True).distinct()
    
    context = {
        'form': form,
        'item': item,
        'suppliers': suppliers,
        'medicines': medicines,
        'title': f'Edit {item.medicine_name}'
    }
    return render(request, 'inventory_form.html', context)

@login_required
def delete_inventory(request, pk):
    """Enhanced delete with confirmation"""
    item = get_object_or_404(MedicineInventory, pk=pk)
    
    if request.method == 'POST':
        medicine_name = item.medicine_name
        item.delete()
        messages.success(request, f'Medicine "{medicine_name}" deleted successfully.')
        return redirect('inventory_list')
    
    return render(request, 'confirm_delete.html', {'item': item})

@login_required
def medicine_detail(request, pk):
    """Enhanced medicine detail view with related records"""
    medicine = get_object_or_404(MedicineInventory, pk=pk)
    
    # Get all records for this medicine
    related_records = MedicineInventory.objects.filter(
        medicine_name=medicine.medicine_name
    ).order_by('-date')
    
    # Get dispense history
    dispense_records = DispenseHistory.objects.filter(
        medicine_name=medicine.medicine_name
    ).order_by('-date')[:10]
    
    # Calculate total stock
    total_stock = medicine.balance()
    
    context = {
        'medicine': medicine,
        'related_records': related_records,
        'dispense_records': dispense_records,
        'total_stock': total_stock,
    }
    
    return render(request, 'medicine_detail.html', context)

@login_required
def dispense_history(request):
    """Enhanced dispense history with filtering"""
    history_list = DispenseHistory.objects.select_related('dispensed_by')
    
    # Date filtering
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        history_list = history_list.filter(date__gte=date_from)
    if date_to:
        history_list = history_list.filter(date__lte=date_to)
    
    # Medicine filtering
    medicine = request.GET.get('medicine')
    if medicine:
        history_list = history_list.filter(medicine_name__icontains=medicine)
    
    # Pagination
    paginator = Paginator(history_list, 20)
    page = request.GET.get('page')
    
    try:
        history = paginator.page(page)
    except PageNotAnInteger:
        history = paginator.page(1)
    except EmptyPage:
        history = paginator.page(paginator.num_pages)
    
    context = {
        'history': history,
        'date_from': date_from,
        'date_to': date_to,
        'medicine': medicine,
    }
    
    return render(request, 'dispense_history.html', context)

@login_required
def quick_dispense(request):
    """Quick dispensing form"""
    if request.method == 'POST':
        form = QuickDispenseForm(request.POST)
        if form.is_valid():
            # Check if medicine exists and has sufficient stock
            try:
                inventory_item = MedicineInventory.objects.filter(
                    medicine_name=form.cleaned_data['medicine_name'],
                    batch_no=form.cleaned_data['batch_no']
                ).first()
                
                if not inventory_item:
                    messages.error(request, 'Medicine with specified batch number not found.')
                    return render(request, 'quick_dispense.html', {'form': form})
                
                if inventory_item.balance() < form.cleaned_data['quantity']:
                    messages.error(request, 'Insufficient stock available.')
                    return render(request, 'quick_dispense.html', {'form': form})
                
                # Create dispense record
                MedicineInventory.objects.create(
                    date=timezone.now().date(),
                    medicine_name=form.cleaned_data['medicine_name'],
                    dosage_form=inventory_item.dosage_form,
                    batch_no=form.cleaned_data['batch_no'],
                    expiry_date=inventory_item.expiry_date,
                    quantity_in=0,
                    quantity_out=form.cleaned_data['quantity'],
                    dispensed_to=form.cleaned_data['patient_name'],
                    prescribing_doctor=form.cleaned_data['prescribing_doctor'],
                    created_by=request.user
                )
                
                # Create dispense history
                DispenseHistory.objects.create(
                    medicine_name=form.cleaned_data['medicine_name'],
                    dosage_form=inventory_item.dosage_form,
                    batch_no=form.cleaned_data['batch_no'],
                    dispensed_to=form.cleaned_data['patient_name'],
                    quantity_out=form.cleaned_data['quantity'],
                    dispensed_by=request.user,
                    prescribing_doctor=form.cleaned_data['prescribing_doctor']
                )
                
                messages.success(request, f'Dispensed {form.cleaned_data["quantity"]} units of {form.cleaned_data["medicine_name"]} to {form.cleaned_data["patient_name"]}.')
                return redirect('inventory_list')
                
            except Exception as e:
                messages.error(request, f'Error processing dispense: {str(e)}')
    else:
        form = QuickDispenseForm()
    
    return render(request, 'quick_dispense.html', {'form': form})

@login_required
def dashboard(request):
    """Enhanced dashboard with analytics and insights"""
    from django.db.models import Sum, Count, Avg, F
    from datetime import timedelta
    
    # Basic statistics
    total_medicines = MedicineInventory.objects.values('medicine_name').distinct().count()
    total_inventory_value = MedicineInventory.objects.aggregate(
        total=Sum(F('quantity_in') * F('unit_cost'))
    )['total'] or 0
    
    # Expiry analysis
    today = timezone.now().date()
    expired_items = MedicineInventory.objects.filter(expiry_date__lte=today)
    expiring_soon = MedicineInventory.objects.filter(
        expiry_date__gt=today,
        expiry_date__lte=today + timedelta(days=30)
    )
    
    # Low stock analysis
    low_stock_items = []
    for item in MedicineInventory.objects.all():
        if item.is_low_stock:
            low_stock_items.append(item)
    
    # Recent activity
    recent_additions = MedicineInventory.objects.filter(
        quantity_in__gt=0,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).order_by('-created_at')[:5]
    
    recent_dispenses = DispenseHistory.objects.filter(
        date__gte=timezone.now() - timedelta(days=7)
    ).order_by('-date')[:5]
    
    # Top medicines by usage
    top_dispensed = DispenseHistory.objects.values('medicine_name').annotate(
        total_dispensed=Sum('quantity_out')
    ).order_by('-total_dispensed')[:5]
    
    # Monthly trends
    monthly_additions = MedicineInventory.objects.filter(
        quantity_in__gt=0,
        date__gte=today - timedelta(days=30)
    ).aggregate(total=Sum('quantity_in'))['total'] or 0
    
    monthly_dispenses = DispenseHistory.objects.filter(
        date__gte=today - timedelta(days=30)
    ).aggregate(total=Sum('quantity_out'))['total'] or 0
    
    # Alerts and notifications
    alerts = []
    
    # Add expired items alerts
    for item in expired_items[:5]:
        alerts.append({
            'type': 'danger',
            'icon': 'exclamation-triangle',
            'message': f'{item.medicine_name} (Batch: {item.batch_no}) has expired on {item.expiry_date}',
            'action_url': f'/edit/{item.id}/',
            'action_text': 'Update'
        })
    
    # Add expiring soon alerts
    for item in expiring_soon[:5]:
        alerts.append({
            'type': 'warning',
            'icon': 'clock',
            'message': f'{item.medicine_name} (Batch: {item.batch_no}) expires in {item.days_to_expiry} days',
            'action_url': f'/medicine/{item.id}/',
            'action_text': 'View'
        })
    
    # Add low stock alerts
    for item in low_stock_items[:5]:
        alerts.append({
            'type': 'info',
            'icon': 'box',
            'message': f'Low stock: {item.medicine_name} (Balance: {item.balance()})',
            'action_url': f'/add/?medicine_name={item.medicine_name}',
            'action_text': 'Restock'
        })
    
    context = {
        'total_medicines': total_medicines,
        'total_inventory_value': total_inventory_value,
        'expired_count': expired_items.count(),
        'expiring_soon_count': expiring_soon.count(),
        'low_stock_count': len(low_stock_items),
        'recent_additions': recent_additions,
        'recent_dispenses': recent_dispenses,
        'top_dispensed': top_dispensed,
        'monthly_additions': monthly_additions,
        'monthly_dispenses': monthly_dispenses,
        'alerts': alerts[:10],  # Limit to 10 alerts
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def analytics_data(request):
    """Provide JSON data for analytics charts"""
    from datetime import timedelta
    
    # Get date range (last 30 days by default)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Daily dispense data
    daily_dispenses = DispenseHistory.objects.filter(
        date__range=[start_date, end_date]
    ).extra(
        select={'day': "date(date)"}
    ).values('day').annotate(
        total=Sum('quantity_out')
    ).order_by('day')
    
    # Medicine distribution by dosage form
    dosage_distribution = MedicineInventory.objects.values('dosage_form').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Expiry distribution
    today = timezone.now().date()
    expiry_data = {
        'expired': MedicineInventory.objects.filter(expiry_date__lte=today).count(),
        'expiring_soon': MedicineInventory.objects.filter(
            expiry_date__gt=today,
            expiry_date__lte=today + timedelta(days=30)
        ).count(),
        'good': MedicineInventory.objects.filter(
            expiry_date__gt=today + timedelta(days=30)
        ).count(),
    }
    
    data = {
        'daily_dispenses': list(daily_dispenses),
        'dosage_distribution': list(dosage_distribution),
        'expiry_data': expiry_data,
    }
    
    return JsonResponse(data)

@login_required
def stock_alerts(request):
    """Manage stock alerts"""
    alerts = StockAlert.objects.filter(is_acknowledged=False).order_by('-created_at')
    
    if request.method == 'POST':
        alert_id = request.POST.get('alert_id')
        action = request.POST.get('action')
        
        if action == 'acknowledge':
            alert = get_object_or_404(StockAlert, id=alert_id)
            alert.is_acknowledged = True
            alert.acknowledged_by = request.user
            alert.acknowledged_at = timezone.now()
            alert.save()
            messages.success(request, 'Alert acknowledged.')
        
        return redirect('stock_alerts')
    
    context = {
        'alerts': alerts,
    }
    
    return render(request, 'stock_alerts.html', context)

@login_required
def generate_reports(request):
    """Generate various reports"""
    report_type = request.GET.get('type', 'inventory')
    
    if report_type == 'inventory':
        return export_inventory_csv(request)
    elif report_type == 'expiry':
        return export_expiry_report(request)
    elif report_type == 'dispense':
        return export_dispense_report(request)
    else:
        messages.error(request, 'Invalid report type.')
        return redirect('dashboard')

@login_required
def export_expiry_report(request):
    """Export expiry report to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expiry_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Medicine Name', 'Batch No', 'Expiry Date', 'Days to Expiry', 'Status', 'Balance'
    ])
    
    items = MedicineInventory.objects.all().order_by('expiry_date')
    
    for item in items:
        status = 'Expired' if item.is_expired else 'Expiring Soon' if item.days_to_expiry <= 30 else 'Good'
        writer.writerow([
            item.medicine_name, item.batch_no, item.expiry_date,
            item.days_to_expiry, status, item.balance()
        ])
    
    return response

@login_required
def export_dispense_report(request):
    """Export dispense history to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dispense_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Medicine Name', 'Batch No', 'Patient Name', 'Quantity',
        'Dispensed By', 'Prescribing Doctor'
    ])
    
    history = DispenseHistory.objects.all().order_by('-date')
    
    for record in history:
        writer.writerow([
            record.date.strftime('%Y-%m-%d %H:%M'),
            record.medicine_name, record.batch_no, record.dispensed_to,
            record.quantity_out, record.dispensed_by.username if record.dispensed_by else '',
            record.prescribing_doctor
        ])
    
    return response

@login_required
def export_inventory_csv(request):
    """Export inventory to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Medicine Name', 'Generic Name', 'Dosage Form', 'Strength', 'Batch No',
        'Expiry Date', 'Quantity In', 'Quantity Out', 'Balance', 'Supplier',
        'Storage Condition', 'Unit Cost', 'Created By', 'Date Added'
    ])
    
    for item in MedicineInventory.objects.all():
        writer.writerow([
            item.medicine_name, item.generic_name, item.dosage_form, item.strength,
            item.batch_no, item.expiry_date, item.quantity_in, item.quantity_out,
            item.balance(), item.supplier_name, item.storage_condition,
            item.unit_cost, item.created_by.username if item.created_by else '',
            item.date
        ])
    
    return response