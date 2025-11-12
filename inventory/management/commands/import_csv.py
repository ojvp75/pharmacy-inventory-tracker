import csv
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from inventory.models import MedicineInventory, Supplier

class Command(BaseCommand):
    help = 'Import medicines from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--user',
            type=str,
            help='Username of the user to assign as created_by (default: first user)',
            default=None
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        if not os.path.exists(csv_file):
            raise CommandError(f'File "{csv_file}" does not exist.')

        # Get user
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
            except User.DoesNotExist:
                raise CommandError(f'User "{options["user"]}" does not exist.')
        else:
            user = User.objects.first()
            if not user:
                raise CommandError('No users found. Please create a user first.')

        medicines_to_create = []
        suppliers_to_create = []
        existing_suppliers = set(Supplier.objects.values_list('name', flat=True))

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                self.stdout.write(f"Found columns: {reader.fieldnames}")
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Clean and validate data
                        medicine_name = row.get('medicine_name', '').strip()
                        if not medicine_name:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Missing medicine_name, skipping')
                            )
                            continue

                        # Parse date
                        date_str = row.get('date', '').strip()
                        if date_str:
                            try:
                                # Try different date formats
                                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                                    try:
                                        medicine_date = datetime.strptime(date_str, fmt).date()
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    medicine_date = date.today()
                                    self.stdout.write(
                                        self.style.WARNING(f'Row {row_num}: Invalid date format, using today')
                                    )
                            except:
                                medicine_date = date.today()
                        else:
                            medicine_date = date.today()

                        # Parse expiry date
                        expiry_str = row.get('expiry_date', '').strip()
                        if expiry_str:
                            try:
                                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                                    try:
                                        expiry_date = datetime.strptime(expiry_str, fmt).date()
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    # Default to 1 year from now
                                    from datetime import timedelta
                                    expiry_date = date.today() + timedelta(days=365)
                                    self.stdout.write(
                                        self.style.WARNING(f'Row {row_num}: Invalid expiry date, using 1 year from now')
                                    )
                            except:
                                from datetime import timedelta
                                expiry_date = date.today() + timedelta(days=365)
                        else:
                            from datetime import timedelta
                            expiry_date = date.today() + timedelta(days=365)

                        # Parse numeric fields
                        try:
                            quantity_in = int(row.get('quantity_in', 0) or 0)
                        except ValueError:
                            quantity_in = 0

                        try:
                            quantity_out = int(row.get('quantity_out', 0) or 0)
                        except ValueError:
                            quantity_out = 0

                        try:
                            unit_cost = float(row.get('unit_cost', 0) or 0)
                        except ValueError:
                            unit_cost = 0.0

                        # Handle supplier
                        supplier_name = row.get('supplier_name', '').strip()
                        if supplier_name and supplier_name not in existing_suppliers:
                            suppliers_to_create.append(Supplier(name=supplier_name))
                            existing_suppliers.add(supplier_name)

                        # Create medicine record
                        medicine = MedicineInventory(
                            date=medicine_date,
                            medicine_name=medicine_name,
                            dosage_form=row.get('dosage_form', '').strip() or 'Tablet',
                            batch_no=row.get('batch_no', '').strip() or f'BATCH_{row_num}',
                            expiry_date=expiry_date,
                            quantity_in=quantity_in,
                            quantity_out=quantity_out,
                            generic_name=row.get('generic_name', '').strip(),
                            manufacturer=row.get('manufacturer', '').strip(),
                            strength=row.get('strength', '').strip(),
                            unit_cost=unit_cost,
                            supplier_name=supplier_name,
                            storage_condition=row.get('storage_condition', ''),
                            prescribing_doctor=row.get('prescribing_doctor', '').strip(),
                            dispensed_to=row.get('dispensed_to', '').strip(),
                            notes=row.get('notes', '').strip(),
                            created_by=user
                        )
                        medicines_to_create.append(medicine)

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: Error processing row - {str(e)}')
                        )
                        continue

        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')

        # Show summary
        self.stdout.write(f"\nSummary:")
        self.stdout.write(f"- {len(medicines_to_create)} medicines to import")
        self.stdout.write(f"- {len(suppliers_to_create)} new suppliers to create")

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('\nDry run completed. No data was imported.'))
            # Show first few records
            if medicines_to_create:
                self.stdout.write("\nFirst few medicines to be imported:")
                for i, med in enumerate(medicines_to_create[:5]):
                    self.stdout.write(f"  {i+1}. {med.medicine_name} ({med.batch_no}) - {med.quantity_in} units")
            return

        # Confirm before importing
        if medicines_to_create:
            confirm = input(f"\nProceed with importing {len(medicines_to_create)} medicines? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write('Import cancelled.')
                return

            # Import data in a transaction
            try:
                with transaction.atomic():
                    # Create suppliers first
                    if suppliers_to_create:
                        Supplier.objects.bulk_create(suppliers_to_create, ignore_conflicts=True)
                        self.stdout.write(f'Created {len(suppliers_to_create)} suppliers.')

                    # Create medicines
                    MedicineInventory.objects.bulk_create(medicines_to_create)
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully imported {len(medicines_to_create)} medicines.')
                    )

            except Exception as e:
                raise CommandError(f'Error during import: {str(e)}')

        else:
            self.stdout.write(self.style.WARNING('No valid medicines found to import.'))