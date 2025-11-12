#!/bin/bash

# Pharmacy Inventory Tracker - Apache Deployment Script

set -e

echo "🚀 Starting Pharmacy Inventory Tracker Deployment for Apache Server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Configuration variables
PROJECT_NAME="pharmacy-inventory"
PROJECT_DIR="/var/www/$PROJECT_NAME"
APACHE_CONF_DIR="/etc/apache2/sites-available"
DOMAIN_NAME="your-domain.com"

print_step "1. Checking system requirements..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

# Check if Apache is installed
if ! command -v apache2 &> /dev/null; then
    print_warning "Apache2 not found. Installing..."
    apt update
    apt install -y apache2
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is required but not installed"
    exit 1
fi

print_step "2. Installing required packages..."

# Install required system packages
apt update
apt install -y python3-pip python3-venv python3-dev libapache2-mod-wsgi-py3 \
               git curl sqlite3

# Enable required Apache modules
a2enmod wsgi
a2enmod ssl
a2enmod rewrite
a2enmod headers
a2enmod expires

print_step "3. Setting up project directory..."

# Create project directory
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Clone or copy project files (assuming files are already here)
if [ -f "manage.py" ]; then
    print_status "Project files found in current directory"
else
    print_warning "Project files not found. Please ensure the project is in $PROJECT_DIR"
    read -p "Press enter when project files are ready..."
fi

print_step "4. Setting up Python virtual environment..."

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

print_step "5. Configuring environment..."

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_warning "Creating .env file from template..."
    cat > .env << EOF
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=$DOMAIN_NAME,www.$DOMAIN_NAME,localhost,127.0.0.1

# Database configuration (SQLite - no additional config needed)
# DB_NAME=pharmacy_inventory  # Not needed for SQLite
# DB_USER=pharmacy_user       # Not needed for SQLite
# DB_PASSWORD=secure_password # Not needed for SQLite
# DB_HOST=localhost           # Not needed for SQLite
# DB_PORT=5432               # Not needed for SQLite

# Email configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Pharmacy details
PHARMACY_NAME=Your Pharmacy Name
PHARMACY_ADDRESS=Your Address
PHARMACY_PHONE=Your Phone Number
EOF
    print_warning "Please edit .env file with your actual configuration"
    nano .env
fi

print_step "6. Setting up database..."

# Using SQLite - ensure database file has proper permissions
if [ -f "db.sqlite3" ]; then
    print_status "Existing SQLite database found - keeping current data"
    chown www-data:www-data db.sqlite3
    chmod 664 db.sqlite3
else
    print_status "Will create new SQLite database during migration"
fi

print_step "7. Running Django setup..."

# Switch to www-data user for Django operations
sudo -u www-data bash << 'EOF'
source .venv/bin/activate

# Run Django migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
EOF

# Create superuser (only if no superusers exist)
sudo -u www-data bash << 'EOF'
source .venv/bin/activate
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Please create one after deployment.')
    exit(1)
else:
    print('Superuser already exists - skipping creation.')
"
EOF

if [ $? -ne 0 ]; then
    print_warning "No superuser exists. You can create one later with:"
    echo "cd $PROJECT_DIR && source .venv/bin/activate && python manage.py createsuperuser"
fi

print_step "8. Setting up file permissions..."

# Set proper permissions
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 644 $PROJECT_DIR/staticfiles
chmod -R 755 $PROJECT_DIR/logs

# Make manage.py executable
chmod +x manage.py

print_step "9. Configuring Apache..."

# Create Apache configuration
cat > $APACHE_CONF_DIR/pharmacy-inventory.conf << EOF
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
    
    # File upload limit (for ODS imports)
    LimitRequestBody 52428800
</VirtualHost>
EOF

# Enable the site
a2ensite pharmacy-inventory.conf

# Disable default site (optional)
a2dissite 000-default.conf || true

print_step "10. Testing configuration..."

# Test Apache configuration
apache2ctl configtest

if [ $? -eq 0 ]; then
    print_status "Apache configuration test passed"
else
    print_error "Apache configuration test failed"
    exit 1
fi

print_step "11. Starting services..."

# Restart Apache
systemctl restart apache2
systemctl enable apache2

# Check if Apache is running
if systemctl is-active --quiet apache2; then
    print_status "Apache is running successfully"
else
    print_error "Failed to start Apache"
    exit 1
fi

print_step "12. Setting up log rotation..."

# Create logrotate configuration
cat > /etc/logrotate.d/pharmacy-inventory << EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
EOF

print_status "✅ Deployment completed successfully!"
echo
echo "📋 Deployment Summary:"
echo "===================="
echo "🌐 Domain: http://$DOMAIN_NAME"
echo "📁 Project Directory: $PROJECT_DIR"
echo "🗄️ Database: SQLite (db.sqlite3)"
echo "📊 Admin Panel: http://$DOMAIN_NAME/admin/"
echo
echo "🔧 Next Steps:"
echo "1. Update DNS records to point to this server"
echo "2. Configure SSL certificate (Let's Encrypt recommended)"
echo "3. Update .env file with production settings"
echo "4. Test the application thoroughly"
echo "5. Set up monitoring and backups"
echo
echo "📜 Useful Commands:"
echo "- View Apache logs: tail -f /var/log/apache2/pharmacy_inventory_error.log"
echo "- Restart Apache: systemctl restart apache2"
echo "- Django shell: cd $PROJECT_DIR && source .venv/bin/activate && python manage.py shell"
echo "- Update code: cd $PROJECT_DIR && git pull && source .venv/bin/activate && python manage.py collectstatic --noinput && systemctl restart apache2"
echo
print_status "🎉 Your Pharmacy Inventory Tracker is now live!"
echo "Visit: http://$DOMAIN_NAME"