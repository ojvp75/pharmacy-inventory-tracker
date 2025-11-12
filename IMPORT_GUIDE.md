## Pharmacy Inventory Data Import Guide

### Overview
Your pharmacy inventory system now includes a powerful data import feature that can read ODS (OpenDocument Spreadsheet) files and import the data into your database.

### Import Command Usage

#### Basic Import
```bash
# Activate virtual environment first
source .venv/bin/activate

# Basic import (will import all data)
python manage.py import_ods "Pharmacy Inventory.ods"

# Preview import without making changes (recommended first)
python manage.py import_ods "Pharmacy Inventory.ods" --dry-run

# Clear existing data before import (use with caution!)
python manage.py import_ods "Pharmacy Inventory.ods" --clear-existing
```

#### Import from specific sheet
```bash
# Import from a specific sheet by name
python manage.py import_ods "Pharmacy Inventory.ods" --sheet "Sheet2"

# Import from a specific sheet by index (0-based)
python manage.py import_ods "Pharmacy Inventory.ods" --sheet 1
```

### Expected File Format

Your ODS file should have these columns (in any order):

| Column Name | Description | Example |
|------------|-------------|---------|
| Date | Transaction date | 2024-01-15 |
| Medicine Name | Name of the medicine | Amoxicillin |
| Dosage/Form | Strength and form | 500mg Capsule |
| Batch No. | Batch or lot number | AMX001 |
| Expiry Date | Expiration date | 2026-01-15 |
| Quantity In | Units received | 100 |
| Quantity Out | Units dispensed | 10 |
| Storage conditions | Storage requirements | Room temperature |
| Supplier name | Supplier name | PharmaCorp Ltd |
| Dispensed By | Who dispensed it | Dr. Smith |
| Notes | Additional comments | For patient J.D. |

### Data Types and Formats

- **Dates**: Use YYYY-MM-DD format (e.g., 2024-01-15)
- **Numbers**: Plain integers (e.g., 100, 10)
- **Text**: Plain text fields
- **Empty cells**: Leave blank if no data

### Import Behavior

1. **Automatic Column Detection**: The system automatically detects which columns contain which data based on column names
2. **Template Data Filtering**: Automatically skips rows with template/example data
3. **Validation**: Validates dates, numbers, and required fields
4. **Error Handling**: Continues importing even if some rows have errors
5. **Dispense History**: Automatically creates dispense history records for transactions with Quantity Out > 0

### Tips for Best Results

1. **Always use --dry-run first** to preview what will be imported
2. **Clean your data**: Remove any template rows or invalid data
3. **Use consistent formats**: Especially for dates and numbers
4. **Check column names**: Make sure they match the expected format
5. **Backup your database** before large imports

### Current File Status

Your current "Pharmacy Inventory.ods" file contains template data that will be automatically skipped. 

To import real data:
1. Open the ODS file in LibreOffice Calc or Excel
2. Replace the template row with your actual inventory data
3. Add as many rows as needed
4. Save the file
5. Run the import command

### Example Real Data

Replace the template row with data like this:

```
Date        | Medicine Name | Dosage/Form   | Batch No. | Expiry Date | Quantity In | Quantity Out | Storage conditions | Supplier name | Dispensed By | Notes
2024-01-15  | Amoxicillin  | 500mg Capsule | AMX001    | 2026-01-15  | 100         | 0            | Room temperature   | PharmaCorp   |              | Initial stock
2024-01-16  | Paracetamol  | 500mg Tablet  | PCM002    | 2025-12-01  | 200         | 0            | Room temperature   | MediSupply   |              | Bulk purchase
2024-01-17  | Amoxicillin  | 500mg Capsule | AMX001    | 2026-01-15  | 0           | 10           | Room temperature   | PharmaCorp   | Dr. Smith    | Patient prescription
```

### Troubleshooting

If you encounter issues:

1. Check the column names match the expected format
2. Verify date formats are YYYY-MM-DD
3. Ensure numeric fields contain only numbers
4. Use --dry-run to preview before importing
5. Check the terminal output for specific error messages

The import system is robust and will give you detailed feedback about what's being imported and any issues encountered.