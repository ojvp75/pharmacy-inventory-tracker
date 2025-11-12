from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('medicine/<int:pk>/', views.medicine_detail, name='medicine_detail'),
    path('add/', views.add_inventory, name='add_inventory'),
    path('edit/<int:pk>/', views.edit_inventory, name='edit_inventory'),
    path('delete/<int:pk>/', views.delete_inventory, name='delete_inventory'),
    path('dispense-history/', views.dispense_history, name='dispense_history'),
    path('quick-dispense/', views.quick_dispense, name='quick_dispense'),
    path('alerts/', views.stock_alerts, name='stock_alerts'),
    path('analytics-data/', views.analytics_data, name='analytics_data'),
    path('reports/', views.generate_reports, name='generate_reports'),
    path('export-csv/', views.export_inventory_csv, name='export_csv'),
]