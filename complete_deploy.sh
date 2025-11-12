#!/bin/bash

# Complete Production Deployment Script for Pharmacy Inventory Tracker
# This script handles the entire deployment process from GitHub to Apache server

set -e

echo "🚀 Complete Pharmacy Inventory Tracker Production Deployment"
echo "============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Configuration
PROJECT_NAME="pharmacy-inventory"
PROJECT_DIR="/var/www/$PROJECT_NAME"
GITHUB_REPO="https://github.com/ojvp75/pharmacy-inventory-tracker.git"
DOMAIN_NAME="your-domain.com"  # Change this to your actual domain

print_step "1. System Requirements Check"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   print_status "Usage: sudo ./complete_deploy.sh"
   exit 1
fi

print_status "Running as root ✓"

print_step "2. Installing System Dependencies"

# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y \
    apache2 \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libapache2-mod-wsgi-py3 \
    sqlite3 \
    git \
    curl \
    nano \
    ufw \
    certbot \
    python3-certbot-apache

print_status "System dependencies installed ✓"

print_step "3. Configuring Apache Modules"

# Enable required Apache modules
a2enmod wsgi
a2enmod ssl
a2enmod rewrite
a2enmod headers
a2enmod expires

print_status "Apache modules enabled ✓"

print_step "4. Cloning Project from GitHub"

# Remove existing directory if it exists
if [ -d "$PROJECT_DIR" ]; then
    print_warning "Existing project directory found. Backing up..."
    mv "$PROJECT_DIR" "${PROJECT_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
fi

# Clone the project
git clone "$GITHUB_REPO" "$PROJECT_DIR"
cd "$PROJECT_DIR"

print_status "Project cloned from GitHub ✓"

print_step "5. Setting up Python Environment"

# Create virtual environment
python3 -m venv .venv

# Change ownership to www-data
chown -R www-data:www-data "$PROJECT_DIR"

# Install Python dependencies
sudo -u www-data bash -c "source .venv/bin/activate && pip install --upgrade pip"
sudo -u www-data bash -c "source .venv/bin/activate && pip install -r requirements.txt"

print_status "Python environment setup complete ✓"

print_step "6. Creating Required Directories"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/media"
mkdir -p "$PROJECT_DIR/staticfiles"

# Set proper permissions
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR/logs"

print_status "Directories created ✓"

print_step "7. Configuring Environment Variables"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cat > .env << EOF
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=$DOMAIN_NAME,www.$DOMAIN_NAME,localhost,127.0.0.1

# Email configuration (update with your settings)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Pharmacy details
PHARMACY_NAME=Your Pharmacy Name
PHARMACY_ADDRESS=Your Complete Address
PHARMACY_PHONE=+1234567890
EOF
    
    print_warning "Created .env file. Please update it with your actual settings:"
    print_status "nano $PROJECT_DIR/.env"
    read -p "Press Enter after you've updated the .env file..."
fi

# Secure the .env file
chown www-data:www-data .env
chmod 600 .env

print_status "Environment configured ✓"

print_step "8. Django Setup"

# Run Django setup commands
sudo -u www-data bash << 'EOF'
source .venv/bin/activate

# Set production settings
export DJANGO_SETTINGS_MODULE=pharmacy_inventory.settings_production

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Test the setup
python manage.py check --deploy
EOF

print_status "Django setup complete ✓"

print_step "9. Creating Superuser"

# Check if superuser exists
sudo -u www-data bash << 'EOF'
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=pharmacy_inventory.settings_production

python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found.')
    exit(1)
else:
    print('Superuser already exists - skipping creation.')
"
EOF

if [ $? -ne 0 ]; then
    print_warning "Creating superuser account..."
    sudo -u www-data bash -c "source .venv/bin/activate && export DJANGO_SETTINGS_MODULE=pharmacy_inventory.settings_production && python manage.py createsuperuser"
fi

print_step "10. Configuring Apache Virtual Host"

# Create Apache configuration
cat > /etc/apache2/sites-available/pharmacy-inventory.conf << EOF
<VirtualHost *:80>
    ServerName $DOMAIN_NAME
    ServerAlias www.$DOMAIN_NAME
    DocumentRoot $PROJECT_DIR
    
    # Static files
    Alias /static $PROJECT_DIR/staticfiles
    <Directory $PROJECT_DIR/staticfiles>
        Require all granted
        ExpiresActive On
        ExpiresByType text/css "access plus 1 year"
        ExpiresByType application/javascript "access plus 1 year"
        ExpiresByType image/png "access plus 1 year"
        ExpiresByType image/jpg "access plus 1 year"
        ExpiresByType image/jpeg "access plus 1 year"
        ExpiresByType image/gif "access plus 1 year"
    </Directory>
    
    # Media files
    Alias /media $PROJECT_DIR/media
    <Directory $PROJECT_DIR/media>
        Require all granted
    </Directory>
    
    # WSGI Configuration
    WSGIDaemonProcess pharmacy_inventory python-home=$PROJECT_DIR/.venv python-path=$PROJECT_DIR
    WSGIProcessGroup pharmacy_inventory
    WSGIScriptAlias / $PROJECT_DIR/pharmacy_inventory/wsgi.py
    
    <Directory $PROJECT_DIR/pharmacy_inventory>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>
    
    # Security headers
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy strict-origin-when-cross-origin
    
    # Logging
    ErrorLog \${APACHE_LOG_DIR}/pharmacy_inventory_error.log
    CustomLog \${APACHE_LOG_DIR}/pharmacy_inventory_access.log combined
    
    # File upload limit (50MB for ODS imports)
    LimitRequestBody 52428800
</VirtualHost>
EOF

# Enable the site
a2ensite pharmacy-inventory.conf
a2dissite 000-default.conf || true

print_status "Apache virtual host configured ✓"

print_step "11. Testing Configuration"

# Test Apache configuration
apache2ctl configtest

if [ $? -eq 0 ]; then
    print_status "Apache configuration test passed ✓"
else
    print_error "Apache configuration test failed"
    exit 1
fi

print_step "12. Setting up Firewall"

# Configure UFW firewall
ufw --force enable
ufw allow 'Apache Full'
ufw allow ssh

print_status "Firewall configured ✓"

print_step "13. Starting Services"

# Restart and enable Apache
systemctl restart apache2
systemctl enable apache2

# Check if Apache is running
if systemctl is-active --quiet apache2; then
    print_status "Apache is running successfully ✓"
else
    print_error "Failed to start Apache"
    exit 1
fi

print_step "14. Setting up SSL (Optional)"

read -p "Do you want to set up SSL with Let's Encrypt? (y/n): " setup_ssl

if [[ $setup_ssl =~ ^[Yy]$ ]]; then
    print_status "Setting up SSL certificate..."
    certbot --apache -d "$DOMAIN_NAME" -d "www.$DOMAIN_NAME" --non-interactive --agree-tos --email admin@"$DOMAIN_NAME"
    
    if [ $? -eq 0 ]; then
        print_status "SSL certificate installed ✓"
    else
        print_warning "SSL setup failed - you can configure it manually later"
    fi
fi

print_step "15. Setting up Automated Backups"

# Create backup script
cat > /usr/local/bin/backup_pharmacy_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/pharmacy"
PROJECT_DIR="/var/www/pharmacy-inventory"

mkdir -p $BACKUP_DIR

# Backup database
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    cp "$PROJECT_DIR/db.sqlite3" "$BACKUP_DIR/pharmacy_backup_$(date +%Y%m%d_%H%M%S).sqlite3"
    
    # Keep only last 30 days of backups
    find $BACKUP_DIR -name "pharmacy_backup_*.sqlite3" -mtime +30 -delete
    
    echo "$(date): Database backup completed" >> /var/log/pharmacy_backup.log
else
    echo "$(date): Database file not found" >> /var/log/pharmacy_backup.log
fi
EOF

chmod +x /usr/local/bin/backup_pharmacy_db.sh

# Add to crontab for daily backups at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup_pharmacy_db.sh") | crontab -

print_status "Automated backups configured ✓"

print_step "16. Final Setup"

# Set final permissions
chown -R www-data:www-data "$PROJECT_DIR"
chmod 644 "$PROJECT_DIR/db.sqlite3" || true
chmod 755 "$PROJECT_DIR"

# Test the application
print_status "Testing application..."
curl -I "http://localhost" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_status "Application is responding ✓"
else
    print_warning "Application test failed - check Apache logs"
fi

echo
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "====================================="
echo
echo "📋 Deployment Summary:"
echo "🌐 Domain: http://$DOMAIN_NAME"
echo "📁 Project Directory: $PROJECT_DIR"
echo "🗄️ Database: SQLite (db.sqlite3)"
echo "📊 Admin Panel: http://$DOMAIN_NAME/admin/"
echo "📚 Documentation: Available in project directory"
echo
echo "🔧 Important Next Steps:"
echo "1. Update DNS records to point $DOMAIN_NAME to this server"
echo "2. Upload your database file (db.sqlite3) to $PROJECT_DIR/"
echo "3. Update .env file with your actual email/pharmacy settings"
echo "4. Test the application thoroughly"
echo "5. Set up monitoring and additional backups"
echo
echo "📜 Useful Commands:"
echo "- View logs: tail -f /var/log/apache2/pharmacy_inventory_error.log"
echo "- Restart Apache: systemctl restart apache2"
echo "- Update code: cd $PROJECT_DIR && git pull && systemctl restart apache2"
echo "- Django shell: cd $PROJECT_DIR && sudo -u www-data bash -c 'source .venv/bin/activate && python manage.py shell'"
echo
echo "🔒 Security Notes:"
echo "- Database backups are scheduled daily at 2 AM"
echo "- Firewall is configured to allow HTTP/HTTPS and SSH only"
echo "- All files are owned by www-data user"
echo "- .env file has restricted permissions (600)"
echo
print_status "🎊 Your Pharmacy Inventory Tracker is now LIVE!"

if [ -n "$DOMAIN_NAME" ] && [ "$DOMAIN_NAME" != "your-domain.com" ]; then
    echo "Visit: http://$DOMAIN_NAME"
else
    echo "Visit: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR-SERVER-IP')"
fi