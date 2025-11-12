"""
Apache WSGI configuration for Pharmacy Inventory Tracker

This module contains the WSGI application used by Apache server.
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

# Add the project path to Python path
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_inventory.settings')

# Get the Django WSGI application
application = get_wsgi_application()

# For Apache mod_wsgi, we can add additional configuration here if needed
# For example, environment variables, logging setup, etc.