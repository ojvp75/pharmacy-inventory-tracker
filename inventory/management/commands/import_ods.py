"""
Management command to import pharmacy inventory data from ODS file
Usage: python manage.py import_ods "Pharmacy Inventory.ods"
"""

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.models import User
from inventory.models import MedicineInventory, DispenseHistory, Supplier
from datetime import datetime
import logging

logger = logging.getLogger('inventory')


class Command(BaseCommand):
    help = 'Import pharmacy inventory data from ODS file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the ODS file to import'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=0,
            help='Sheet name or index to import (default: first sheet)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview the import without making changes'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing inventory data before import'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        sheet = options['sheet']
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']

        self.stdout.write(f'Starting import from: {file_path}')

        try:
            # Read the ODS file
            if isinstance(sheet, str) and sheet.isdigit():
                sheet = int(sheet)
            
            df = pd.read_excel(file_path, sheet_name=sheet, engine='odf')
            
            self.stdout.write(f'Found {len(df)} rows in the file')
            self.stdout.write('Columns in the file:')
            for i, col in enumerate(df.columns):
                self.stdout.write(f'  {i}: {col}')

            # Show first few rows for preview
            self.stdout.write('\nFirst 5 rows:')
            self.stdout.write(str(df.head()))
            
            if dry_run:
                self.stdout.write('\n--- DRY RUN MODE - No data will be imported ---')
                self.preview_import(df)
                return

            # Get or create a default user for import
            try:
                import_user = User.objects.get(username='admin')
            except User.DoesNotExist:
                import_user = User.objects.first()
                if not import_user:
                    raise CommandError('No users found. Please create a user first.')

            # Clear existing data if requested
            if clear_existing:
                self.stdout.write('Clearing existing inventory data...')
                MedicineInventory.objects.all().delete()
                DispenseHistory.objects.all().delete()

            # Import the data
            imported_count = self.import_data(df, import_user)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully imported {imported_count} records')
            )

        except Exception as e:
            raise CommandError(f'Error importing data: {str(e)}')

    def preview_import(self, df):
        """Preview what would be imported"""
        self.stdout.write('\nPreview of import mapping:')
        
        # Try to identify columns automatically
        column_mapping = self.detect_columns(df)
        
        for field, column in column_mapping.items():
            if column:
                self.stdout.write(f'  {field}: Column "{column}"')
            else:
                self.stdout.write(f'  {field}: NOT FOUND')

        # Show sample data
        if len(df) > 0:
            self.stdout.write('\nSample record that would be imported:')
            sample_record = self.map_row_to_medicine(df.iloc[0], column_mapping)
            for field, value in sample_record.items():
                self.stdout.write(f'  {field}: {value}')

    def detect_columns(self, df):
        """Automatically detect column mappings"""
        columns = [col.lower() for col in df.columns]
        
        mapping = {
            'medicine_name': None,
            'generic_name': None,
            'dosage_form': None,
            'strength': None,
            'batch_no': None,
            'expiry_date': None,
            'quantity_in': None,
            'quantity_out': None,
            'supplier_name': None,
            'storage_condition': None,
            'unit_cost': None,
            'date': None,
            'dispensed_to': None,
            'dispensed_by': None,
            'prescribing_doctor': None,
            'manufacturer': None,
            'notes': None
        }

        # Common column name patterns
        patterns = {
            'medicine_name': ['medicine name', 'medicine', 'drug', 'medication', 'name', 'medicine_name', 'drug_name'],
            'generic_name': ['generic', 'generic_name', 'scientific_name'],
            'dosage_form': ['dosage/form', 'dosage', 'form', 'dosage_form', 'type'],
            'strength': ['strength', 'dose', 'concentration'],
            'batch_no': ['batch no.', 'batch no', 'batch', 'lot', 'batch_no', 'lot_no', 'batch_number'],
            'expiry_date': ['expiry date', 'expiry', 'expire', 'expiration', 'exp_date', 'expiry_date'],
            'quantity_in': ['quantity in', 'qty_in', 'quantity_in', 'stock_in', 'received', 'in'],
            'quantity_out': ['quantity out', 'qty_out', 'quantity_out', 'stock_out', 'dispensed', 'out'],
            'supplier_name': ['supplier name', 'supplier', 'vendor', 'supplier_name'],
            'storage_condition': ['storage conditions', 'storage', 'condition', 'storage_condition'],
            'unit_cost': ['cost', 'price', 'unit_cost', 'unit_price'],
            'date': ['date', 'transaction_date', 'entry_date'],
            'dispensed_to': ['dispensed to', 'patient', 'dispensed_to', 'customer'],
            'dispensed_by': ['dispensed by', 'dispensed_by', 'pharmacist'],
            'prescribing_doctor': ['doctor', 'physician', 'prescriber', 'prescribing_doctor'],
            'manufacturer': ['manufacturer', 'company', 'mfg'],
            'notes': ['notes', 'remarks', 'comments', 'description']
        }

        for field, search_terms in patterns.items():
            for term in search_terms:
                for i, col in enumerate(columns):
                    if term in col:
                        mapping[field] = df.columns[i]  # Use original column name
                        break
                if mapping[field]:
                    break

        return mapping

    def map_row_to_medicine(self, row, column_mapping):
        """Map a pandas row to medicine inventory fields"""
        data = {}
        
        for field, column in column_mapping.items():
            if column and column in row.index:
                value = row[column]
                if pd.notna(value):
                    data[field] = value
                else:
                    data[field] = ''
            else:
                data[field] = ''

        return data

    def import_data(self, df, import_user):
        """Import the actual data"""
        column_mapping = self.detect_columns(df)
        imported_count = 0

        for index, row in df.iterrows():
            try:
                data = self.map_row_to_medicine(row, column_mapping)
                
                # Skip rows without essential data or template data
                if not data.get('medicine_name'):
                    self.stdout.write(f'Skipping row {index + 1}: No medicine name')
                    continue
                
                # Skip template/example rows
                medicine_name = str(data.get('medicine_name', '')).strip()
                if (medicine_name.startswith('e.g.') or 
                    medicine_name == 'YYYY-MM-DD' or 
                    'example' in medicine_name.lower() or
                    'template' in medicine_name.lower()):
                    self.stdout.write(f'Skipping row {index + 1}: Template/example data')
                    continue

                # Parse dates
                date_value = self.parse_date(data.get('date'))
                expiry_date = self.parse_date(data.get('expiry_date'))

                if not expiry_date:
                    self.stdout.write(f'Skipping row {index + 1}: No valid expiry date')
                    continue

                # Create medicine inventory record
                medicine = MedicineInventory(
                    medicine_name=str(data.get('medicine_name', '')).strip(),
                    generic_name=str(data.get('generic_name', '')).strip(),
                    dosage_form=str(data.get('dosage_form', '')).strip(),
                    strength=str(data.get('strength', '')).strip(),
                    manufacturer=str(data.get('manufacturer', '')).strip(),
                    batch_no=str(data.get('batch_no', '')).strip(),
                    expiry_date=expiry_date,
                    quantity_in=self.parse_number(data.get('quantity_in', 0)),
                    quantity_out=self.parse_number(data.get('quantity_out', 0)),
                    supplier_name=str(data.get('supplier_name', '')).strip(),
                    storage_condition=str(data.get('storage_condition', '')).strip(),
                    unit_cost=self.parse_decimal(data.get('unit_cost')),
                    date=date_value or timezone.now().date(),
                    dispensed_to=str(data.get('dispensed_to', '')).strip(),
                    prescribing_doctor=str(data.get('prescribing_doctor', '')).strip(),
                    notes=str(data.get('notes', '')).strip(),
                    created_by=import_user
                )

                medicine.save()
                imported_count += 1

                # Create dispense history if quantity_out > 0
                if medicine.quantity_out > 0 and medicine.dispensed_to:
                    DispenseHistory.objects.create(
                        medicine_name=medicine.medicine_name,
                        dosage_form=medicine.dosage_form,
                        batch_no=medicine.batch_no,
                        dispensed_to=medicine.dispensed_to,
                        quantity_out=medicine.quantity_out,
                        dispensed_by=import_user,
                        prescribing_doctor=medicine.prescribing_doctor,
                        inventory_record=medicine
                    )

                if imported_count % 10 == 0:
                    self.stdout.write(f'Imported {imported_count} records...')

            except Exception as e:
                self.stdout.write(f'Error importing row {index + 1}: {str(e)}')
                continue

        return imported_count

    def parse_date(self, date_value):
        """Parse various date formats"""
        if pd.isna(date_value) or not date_value:
            return None

        if isinstance(date_value, datetime):
            return date_value.date()

        if isinstance(date_value, str):
            # Try common date formats
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']
            for fmt in formats:
                try:
                    return datetime.strptime(date_value.strip(), fmt).date()
                except ValueError:
                    continue

        return None

    def parse_number(self, value):
        """Parse numeric values"""
        if pd.isna(value) or value == '':
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def parse_decimal(self, value):
        """Parse decimal values"""
        if pd.isna(value) or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None