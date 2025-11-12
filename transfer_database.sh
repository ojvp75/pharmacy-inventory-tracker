#!/bin/bash

# Database Transfer Script for Pharmacy Inventory Tracker
# This script helps transfer your SQLite database to the production server

echo "📦 Database Transfer Helper for Pharmacy Inventory Tracker"
echo "=========================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
LOCAL_DB_PATH="/Users/osvaldo/Documents/scripts/Pharmacy_Inventory_Tracker/pharmacy_inventory/db.sqlite3"
SERVER_USER="your-username"  # Change this
SERVER_HOST="your-server.com"  # Change this
SERVER_PROJECT_DIR="/var/www/pharmacy-inventory"

echo "This script will help you transfer your database to the production server."
echo "Please ensure you have:"
echo "1. SSH access to your server"
echo "2. The production deployment is complete"
echo "3. Your server details are correct"
echo

read -p "Enter your server username: " SERVER_USER
read -p "Enter your server hostname/IP: " SERVER_HOST

print_status "Using server: $SERVER_USER@$SERVER_HOST"

# Method 1: Transfer to user home directory first, then move
print_status "Method 1: Safe Transfer via Home Directory"
echo "Step 1: Transfer database to your home directory on server"

if [ -f "$LOCAL_DB_PATH" ]; then
    print_status "Found local database: $LOCAL_DB_PATH"
    
    # Get database info
    echo "Database information:"
    ls -lh "$LOCAL_DB_PATH"
    
    echo
    print_status "Transferring database to server home directory..."
    
    # Copy to server home directory first
    scp "$LOCAL_DB_PATH" "$SERVER_USER@$SERVER_HOST:~/pharmacy_db_backup.sqlite3"
    
    if [ $? -eq 0 ]; then
        print_status "✓ Database transferred successfully to server home directory"
        
        echo
        print_status "Step 2: Moving database to production directory"
        print_warning "You'll need to run these commands on your server:"
        echo
        echo "# SSH to your server:"
        echo "ssh $SERVER_USER@$SERVER_HOST"
        echo
        echo "# Move database to production directory:"
        echo "sudo cp ~/pharmacy_db_backup.sqlite3 $SERVER_PROJECT_DIR/db.sqlite3"
        echo "sudo chown www-data:www-data $SERVER_PROJECT_DIR/db.sqlite3"
        echo "sudo chmod 664 $SERVER_PROJECT_DIR/db.sqlite3"
        echo
        echo "# Verify the transfer:"
        echo "sudo ls -la $SERVER_PROJECT_DIR/db.sqlite3"
        echo
        echo "# Test the database:"
        echo "cd $SERVER_PROJECT_DIR"
        echo "sudo -u www-data bash -c 'source .venv/bin/activate && python manage.py shell -c \"from inventory.models import MedicineInventory; print(f\\\"Records: {MedicineInventory.objects.count()}\\\")\"'"
        echo
        echo "# Clean up temporary file:"
        echo "rm ~/pharmacy_db_backup.sqlite3"
        echo
        echo "# Restart Apache:"
        echo "sudo systemctl restart apache2"
        
    else
        print_error "Failed to transfer database"
        echo
        print_status "Alternative methods:"
        echo
        print_status "Method 2: Using rsync"
        echo "rsync -avz '$LOCAL_DB_PATH' '$SERVER_USER@$SERVER_HOST:~/pharmacy_db_backup.sqlite3'"
        echo
        print_status "Method 3: Manual upload using SFTP client"
        echo "- Use FileZilla, WinSCP, or similar"
        echo "- Upload to your home directory first"
        echo "- Then move using SSH commands above"
    fi
    
else
    print_error "Local database not found at: $LOCAL_DB_PATH"
    print_status "Looking for database files..."
    find /Users/osvaldo/Documents/scripts/Pharmacy_Inventory_Tracker -name "*.sqlite3" 2>/dev/null
fi

echo
print_warning "IMPORTANT SECURITY NOTES:"
echo "- Your database contains sensitive pharmacy data"
echo "- Always use encrypted connections (SCP/SFTP)"
echo "- Verify file integrity after transfer"
echo "- Set proper permissions (664) and ownership (www-data)"
echo "- Create a backup before replacing existing database"

echo
print_status "After successful transfer, test your application:"
echo "1. Visit your website and try to login"
echo "2. Check the inventory list to see your data"
echo "3. Test adding a new medicine record"
echo "4. Check Apache error logs if there are issues:"
echo "   sudo tail -f /var/log/apache2/pharmacy_inventory_error.log"