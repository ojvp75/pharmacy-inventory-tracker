# Apache Deployment Guide for Pharmacy Inventory Tracker

This guide provides comprehensive instructions for deploying the Pharmacy Inventory Tracker on an Apache web server.

## Prerequisites

- Ubuntu/Debian server (18.04+ or 20.04+)
- Root or sudo access
- Domain name pointing to your server
- Basic knowledge of Linux command line

## Quick Deployment

For automated deployment, run:

```bash
sudo chmod +x deploy_apache.sh
sudo ./deploy_apache.sh
```

## Manual Deployment Steps

### 1. System Requirements

Update your system and install required packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y apache2 python3 python3-pip python3-venv python3-dev \
                    libapache2-mod-wsgi-py3 sqlite3 git curl nano
```

### 2. Enable Apache Modules

```bash
sudo a2enmod wsgi
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers
sudo a2enmod expires
```

### 3. Setup Project Directory

```bash
sudo mkdir -p /var/www/pharmacy-inventory
cd /var/www/pharmacy-inventory

# Upload or clone your project files here
# If using git:
# sudo git clone https://github.com/yourusername/pharmacy-inventory-tracker.git .
```

### 4. Setup Python Environment

```bash
sudo python3 -m venv .venv
sudo chown -R www-data:www-data /var/www/pharmacy-inventory
sudo -u www-data bash -c "source .venv/bin/activate && pip install --upgrade pip"
sudo -u www-data bash -c "source .venv/bin/activate && pip install -r requirements.txt"
```

### 5. Configure Environment Variables

Create `.env` file:

```bash
sudo -u www-data nano /var/www/pharmacy-inventory/.env
```

Add the following content:

```env
SECRET_KEY=your-super-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost

# Database (SQLite - no configuration needed)
# Using SQLite database - db.sqlite3 file will be created automatically

# Email settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Pharmacy details
PHARMACY_NAME=Your Pharmacy Name
PHARMACY_ADDRESS=Your Complete Address
PHARMACY_PHONE=+1234567890
```

### 6. Setup Database (SQLite)

No additional database setup is required for SQLite. The database file will be created automatically during Django migration. Just ensure proper permissions:

```bash
# If you have an existing db.sqlite3 file, set proper permissions:
sudo chown www-data:www-data /var/www/pharmacy-inventory/db.sqlite3
sudo chmod 664 /var/www/pharmacy-inventory/db.sqlite3

# Ensure the directory is writable by www-data
sudo chown www-data:www-data /var/www/pharmacy-inventory
```

### 7. Django Setup

```bash
cd /var/www/pharmacy-inventory
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py makemigrations"
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py migrate"
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py collectstatic --noinput"
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py createsuperuser"
```

### 8. Configure Apache Virtual Host

Create the Apache configuration file:

```bash
sudo nano /etc/apache2/sites-available/pharmacy-inventory.conf
```

Add this configuration (replace `yourdomain.com` with your actual domain):

```apache
<VirtualHost *:80>
    ServerName yourdomain.com
    ServerAlias www.yourdomain.com
    DocumentRoot /var/www/pharmacy-inventory
    
    # Static files
    Alias /static /var/www/pharmacy-inventory/staticfiles
    <Directory /var/www/pharmacy-inventory/staticfiles>
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
    Alias /media /var/www/pharmacy-inventory/media
    <Directory /var/www/pharmacy-inventory/media>
        Require all granted
    </Directory>
    
    # WSGI Configuration
    WSGIDaemonProcess pharmacy_inventory python-home=/var/www/pharmacy-inventory/.venv python-path=/var/www/pharmacy-inventory
    WSGIProcessGroup pharmacy_inventory
    WSGIScriptAlias / /var/www/pharmacy-inventory/pharmacy_inventory/wsgi.py
    
    <Directory /var/www/pharmacy-inventory/pharmacy_inventory>
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
    ErrorLog ${APACHE_LOG_DIR}/pharmacy_inventory_error.log
    CustomLog ${APACHE_LOG_DIR}/pharmacy_inventory_access.log combined
    
    # File upload limit (50MB for ODS imports)
    LimitRequestBody 52428800
</VirtualHost>
```

### 9. Enable Site and Restart Apache

```bash
sudo a2ensite pharmacy-inventory.conf
sudo a2dissite 000-default.conf
sudo apache2ctl configtest
sudo systemctl restart apache2
sudo systemctl enable apache2
```

### 10. Setup SSL (Recommended)

Install Certbot for Let's Encrypt SSL:

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d yourdomain.com -d www.yourdomain.com
```

### 11. File Permissions

Ensure proper file permissions:

```bash
sudo chown -R www-data:www-data /var/www/pharmacy-inventory
sudo chmod -R 755 /var/www/pharmacy-inventory
sudo chmod -R 644 /var/www/pharmacy-inventory/staticfiles
sudo mkdir -p /var/www/pharmacy-inventory/logs
sudo chmod -R 755 /var/www/pharmacy-inventory/logs
```

## Post-Deployment Configuration

### 1. Firewall Setup

```bash
sudo ufw allow 'Apache Full'
sudo ufw allow ssh
sudo ufw --force enable
```

### 2. Log Rotation

Create log rotation configuration:

```bash
sudo nano /etc/logrotate.d/pharmacy-inventory
```

Add:

```
/var/www/pharmacy-inventory/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
```

### 3. Monitoring Setup

Create a simple monitoring script:

```bash
sudo nano /usr/local/bin/check_pharmacy_app.sh
```

Add:

```bash
#!/bin/bash
URL="http://yourdomain.com"
if curl -f -s $URL > /dev/null; then
    echo "$(date): Pharmacy app is running" >> /var/log/pharmacy_monitoring.log
else
    echo "$(date): Pharmacy app is DOWN!" >> /var/log/pharmacy_monitoring.log
    systemctl restart apache2
fi
```

Make it executable and add to cron:

```bash
sudo chmod +x /usr/local/bin/check_pharmacy_app.sh
sudo crontab -e
# Add this line:
# */5 * * * * /usr/local/bin/check_pharmacy_app.sh
```

## Maintenance Commands

### Update Application

```bash
cd /var/www/pharmacy-inventory
sudo git pull  # If using git
sudo -u www-data bash -c "source .venv/bin/activate && pip install -r requirements.txt"
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py migrate"
sudo -u www-data bash -c "source .venv/bin/activate && python manage.py collectstatic --noinput"
sudo systemctl restart apache2
```

### View Logs

```bash
# Apache logs
sudo tail -f /var/log/apache2/pharmacy_inventory_error.log
sudo tail -f /var/log/apache2/pharmacy_inventory_access.log

# Application logs
sudo tail -f /var/www/pharmacy-inventory/logs/pharmacy.log
```

### Backup Database

```bash
# Backup SQLite database
sudo cp /var/www/pharmacy-inventory/db.sqlite3 /var/backups/pharmacy_backup_$(date +%Y%m%d).sqlite3

# Create automated backup script
sudo cat > /usr/local/bin/backup_pharmacy_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/pharmacy"
mkdir -p $BACKUP_DIR
cp /var/www/pharmacy-inventory/db.sqlite3 $BACKUP_DIR/pharmacy_backup_$(date +%Y%m%d_%H%M%S).sqlite3
# Keep only last 30 days of backups
find $BACKUP_DIR -name "pharmacy_backup_*.sqlite3" -mtime +30 -delete
EOF

sudo chmod +x /usr/local/bin/backup_pharmacy_db.sh

# Add to cron for daily backups
echo "0 2 * * * /usr/local/bin/backup_pharmacy_db.sh" | sudo crontab -
```

### Restore Database

```bash
# Stop Apache first
sudo systemctl stop apache2

# Restore from backup
sudo cp /var/backups/pharmacy_backup_YYYYMMDD.sqlite3 /var/www/pharmacy-inventory/db.sqlite3
sudo chown www-data:www-data /var/www/pharmacy-inventory/db.sqlite3
sudo chmod 664 /var/www/pharmacy-inventory/db.sqlite3

# Start Apache
sudo systemctl start apache2
```

## Troubleshooting

### Common Issues

1. **500 Internal Server Error**
   - Check Apache error logs
   - Verify file permissions
   - Check Django logs

2. **Static files not loading**
   - Run `collectstatic` command
   - Check Apache static file alias
   - Verify file permissions

3. **Database connection errors**
   - Check PostgreSQL service status
   - Verify database credentials in `.env`
   - Check firewall settings

4. **Import errors with ODS files**
   - Check file upload limits in Apache
   - Verify pandas and odfpy are installed
   - Check file permissions on media directory

### Performance Optimization

1. **Enable compression:**
```apache
LoadModule deflate_module modules/mod_deflate.so
<Location />
    SetOutputFilter DEFLATE
</Location>
```

2. **Enable caching:**
```apache
LoadModule expires_module modules/mod_expires.so
ExpiresActive On
ExpiresByType text/css "access plus 1 month"
ExpiresByType application/javascript "access plus 1 month"
```

3. **Database optimization:**
   - Configure PostgreSQL for production
   - Set up connection pooling
   - Regular database maintenance

## Security Checklist

- [ ] SSL certificate installed
- [ ] Firewall properly configured
- [ ] Regular backups scheduled
- [ ] Security headers enabled
- [ ] File permissions properly set
- [ ] Debug mode disabled
- [ ] Secret key is secure and unique
- [ ] Database credentials are secure
- [ ] Regular security updates applied

## Contact

For support and questions about this deployment, please refer to the project documentation or create an issue in the project repository.