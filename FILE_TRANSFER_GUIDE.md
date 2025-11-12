# File Transfer Guide for Pharmacy Inventory Tracker

This guide helps you transfer your existing database and project files to the production server.

## Prerequisites

- Access to your production server (SSH)
- Your current project directory with the SQLite database
- Basic knowledge of file transfer methods

## Method 1: Using SCP (Secure Copy)

### 1. Prepare files for transfer

From your local development machine:

```bash
cd /Users/osvaldo/Documents/scripts/Pharmacy_Inventory_Tracker/pharmacy_inventory

# Create a tar archive of the project (excluding virtual environment and logs)
tar -czf pharmacy_inventory.tar.gz \
    --exclude='.venv' \
    --exclude='logs' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    .
```

### 2. Transfer to production server

```bash
# Transfer the archive to your server
scp pharmacy_inventory.tar.gz user@your-server.com:/tmp/

# SSH into your server
ssh user@your-server.com

# Extract files on server
sudo mkdir -p /var/www/pharmacy-inventory
cd /var/www/pharmacy-inventory
sudo tar -xzf /tmp/pharmacy_inventory.tar.gz
sudo chown -R www-data:www-data /var/www/pharmacy-inventory
```

## Method 2: Using Git

### 1. Initialize Git repository (if not already done)

From your local machine:

```bash
cd /Users/osvaldo/Documents/scripts/Pharmacy_Inventory_Tracker/pharmacy_inventory

# Initialize git if not already done
git init

# Add all files (except those in .gitignore)
git add .

# Commit the files
git commit -m "Initial commit - ready for production"
```

### 2. Push to GitHub

```bash
# Create a new repository on GitHub first, then:
git remote add origin https://github.com/yourusername/pharmacy-inventory-tracker.git
git branch -M main
git push -u origin main
```

### 3. Clone on production server

```bash
# SSH into your server
ssh user@your-server.com

# Clone the repository
sudo git clone https://github.com/yourusername/pharmacy-inventory-tracker.git /var/www/pharmacy-inventory
sudo chown -R www-data:www-data /var/www/pharmacy-inventory
```

## Method 3: Using SFTP/FTP Client

You can use graphical FTP clients like:
- FileZilla
- WinSCP (Windows)
- Cyberduck (Mac/Windows)

1. Connect to your server using SFTP
2. Upload the entire project directory to `/var/www/pharmacy-inventory`
3. Set proper permissions via SSH

## Important Files to Transfer

Make sure these key files are transferred:

- `db.sqlite3` - Your database with all the inventory data
- `manage.py` - Django management script
- `pharmacy_inventory/` - Django project directory
- `inventory/` - Django app directory
- `static/` - Static files
- `requirements.txt` - Python dependencies
- `.env.example` - Environment template
- All template and static files

## Post-Transfer Steps

### 1. Set proper permissions

```bash
sudo chown -R www-data:www-data /var/www/pharmacy-inventory
sudo chmod -R 755 /var/www/pharmacy-inventory
sudo chmod 664 /var/www/pharmacy-inventory/db.sqlite3
```

### 2. Create virtual environment

```bash
cd /var/www/pharmacy-inventory
sudo -u www-data python3 -m venv .venv
sudo -u www-data bash -c "source .venv/bin/activate && pip install -r requirements.txt"
```

### 3. Configure environment

```bash
# Copy environment file
sudo cp .env.example .env

# Edit with production settings
sudo nano .env
```

### 4. Run Django setup

```bash
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py collectstatic --noinput"

# Test the database
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py check"
```

## Security Considerations

### 1. Database Security

Your SQLite database may contain sensitive information. Ensure:

```bash
# Set restrictive permissions on database
sudo chmod 660 /var/www/pharmacy-inventory/db.sqlite3
sudo chown www-data:www-data /var/www/pharmacy-inventory/db.sqlite3
```

### 2. Environment Variables

```bash
# Secure the .env file
sudo chmod 600 /var/www/pharmacy-inventory/.env
sudo chown www-data:www-data /var/www/pharmacy-inventory/.env
```

### 3. Remove Development Files

```bash
# Remove any development-only files
sudo rm -rf /var/www/pharmacy-inventory/.venv
sudo rm -rf /var/www/pharmacy-inventory/__pycache__
sudo rm -rf /var/www/pharmacy-inventory/*/__pycache__
```

## Verification Steps

### 1. Test Database Access

```bash
cd /var/www/pharmacy-inventory
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py shell -c 'from inventory.models import MedicineInventory; print(f\"Records: {MedicineInventory.objects.count()}\")'"
```

### 2. Test Static Files

```bash
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py collectstatic --noinput --dry-run"
```

### 3. Test Application

After Apache configuration:

```bash
# Check Apache status
sudo systemctl status apache2

# Test the application
curl -I http://your-domain.com
```

## Troubleshooting

### Database Issues

```bash
# Check database file exists and permissions
ls -la /var/www/pharmacy-inventory/db.sqlite3

# Test database connectivity
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py dbshell"
```

### Permission Issues

```bash
# Reset all permissions
sudo chown -R www-data:www-data /var/www/pharmacy-inventory
sudo find /var/www/pharmacy-inventory -type f -exec chmod 644 {} \;
sudo find /var/www/pharmacy-inventory -type d -exec chmod 755 {} \;
sudo chmod 660 /var/www/pharmacy-inventory/db.sqlite3
```

### File Transfer Issues

```bash
# Check file integrity
md5sum /path/to/original/file
md5sum /path/to/transferred/file

# Check available space
df -h /var/www
```

## Automated Transfer Script

Here's a simple script to automate the transfer:

```bash
#!/bin/bash
# transfer.sh - Automated file transfer script

LOCAL_DIR="/Users/osvaldo/Documents/scripts/Pharmacy_Inventory_Tracker/pharmacy_inventory"
SERVER="user@your-server.com"
REMOTE_DIR="/var/www/pharmacy-inventory"

echo "Creating archive..."
cd $LOCAL_DIR
tar -czf pharmacy_inventory.tar.gz \
    --exclude='.venv' \
    --exclude='logs' \
    --exclude='__pycache__' \
    .

echo "Transferring files..."
scp pharmacy_inventory.tar.gz $SERVER:/tmp/

echo "Extracting on server..."
ssh $SERVER "
    sudo mkdir -p $REMOTE_DIR
    cd $REMOTE_DIR
    sudo tar -xzf /tmp/pharmacy_inventory.tar.gz
    sudo chown -R www-data:www-data $REMOTE_DIR
    sudo chmod 664 $REMOTE_DIR/db.sqlite3
    rm /tmp/pharmacy_inventory.tar.gz
"

echo "Transfer complete!"
```

Make it executable and run:

```bash
chmod +x transfer.sh
./transfer.sh
```

This ensures your existing SQLite database and all data are properly transferred to the production server.