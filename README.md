# Pharmacy Inventory Management System

A comprehensive, modern web-based pharmacy inventory management system built with Django. This system helps pharmacies track medicine inventory, manage dispensing, monitor expiry dates, and maintain detailed records.

## Features

### 📊 Dashboard & Analytics
- Real-time inventory statistics and analytics
- Interactive charts showing dispensing trends
- Medicine distribution by dosage form
- Expiry status overview
- Quick access to key metrics

### 💊 Inventory Management
- Add, edit, and delete medicine records
- Track batch numbers and expiry dates
- Monitor stock levels with automatic low stock alerts
- Advanced filtering and search capabilities
- Bulk export functionality

### 🚀 Quick Dispensing
- Fast medicine dispensing with patient tracking
- Automatic stock level updates
- Prescription and doctor information recording
- Complete dispense history

### 🔔 Smart Alerts
- Automatic expiry date monitoring
- Low stock level notifications
- Expired medicine alerts
- Customizable alert thresholds

### 📱 Modern UI/UX
- Responsive design for all devices
- Professional, clean interface
- Bootstrap-based styling
- Intuitive navigation and workflows

### 🔒 Security Features
- User authentication and session management
- CSRF protection
- Secure cookie settings
- Input validation and sanitization
- Audit logging

### 📈 Reporting & Export
- CSV export for inventory data
- Expiry reports
- Dispensing history reports
- Comprehensive analytics

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pharmacy_inventory
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows:
   .venv\Scripts\activate
   
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configurations
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files (for production)**
   ```bash
   python manage.py collectstatic
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Open your browser and go to `http://localhost:8000`
   - Login with your superuser credentials
   - Start managing your pharmacy inventory!

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example` and configure:

```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost

# Email settings for alerts
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Pharmacy details
PHARMACY_NAME=Your Pharmacy Name
PHARMACY_ADDRESS=Your Address
PHARMACY_PHONE=Your Phone Number

# Alert thresholds
EXPIRY_ALERT_DAYS=30
LOW_STOCK_ALERT_DAYS=7
```

### Database Configuration

By default, the system uses SQLite for development. For production, consider using PostgreSQL:

1. Install PostgreSQL and create a database
2. Install psycopg2: `pip install psycopg2-binary`
3. Update your `.env` file:
   ```env
   DATABASE_URL=postgres://username:password@localhost:5432/pharmacy_db
   ```

## Usage

### Adding Medicines
1. Click "Add Medicine" from the navigation
2. Fill in medicine details (name, batch, expiry, etc.)
3. Enter quantity in (for new stock) or quantity out (for dispensing)
4. Save the record

### Quick Dispensing
1. Use "Quick Dispense" for fast patient dispensing
2. Enter medicine name, batch number, and quantity
3. Add patient information
4. Confirm dispensing

### Monitoring Alerts
1. Check the dashboard for active alerts
2. Review expired and expiring medicines
3. Monitor low stock levels
4. Take action on critical alerts

### Generating Reports
1. Use the export functions for various reports
2. Download CSV files for external analysis
3. Print inventory lists directly from the browser

## Automated Tasks

### Daily Alert Checks
Set up a cron job to run daily alert checks:

```bash
# Add to crontab (crontab -e)
0 9 * * * cd /path/to/pharmacy_inventory && python manage.py check_alerts --send-email
```

This will:
- Check for expired medicines
- Identify medicines expiring soon
- Create low stock alerts
- Send email notifications for critical alerts

### Backup Recommendations
- Set up regular database backups
- Configure file system backups for uploaded documents
- Test restore procedures regularly

## Production Deployment

### Security Checklist
- [ ] Change SECRET_KEY to a secure random value
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS appropriately
- [ ] Use HTTPS (configure SSL certificates)
- [ ] Set up secure database (PostgreSQL recommended)
- [ ] Configure email settings for alerts
- [ ] Set up regular backups
- [ ] Configure logging and monitoring
- [ ] Review and update security headers

### Performance Optimization
- Use a production WSGI server (Gunicorn, uWSGI)
- Configure a reverse proxy (Nginx, Apache)
- Set up database connection pooling
- Configure caching (Redis, Memcached)
- Optimize static file serving

### Example Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /static/ {
        alias /path/to/pharmacy_inventory/staticfiles/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## API Documentation

The system provides JSON API endpoints for analytics:
- `/analytics-data/` - Chart data for dashboard
- `/api/medicines/` - Medicine inventory data (if API is enabled)

## Troubleshooting

### Common Issues

1. **Migration errors**: Run `python manage.py makemigrations` then `python manage.py migrate`
2. **Static files not loading**: Run `python manage.py collectstatic`
3. **Permission errors**: Check file permissions and ownership
4. **Email not working**: Verify SMTP settings and firewall rules

### Logging

Check logs in the `logs/` directory:
- `pharmacy.log` - Application logs
- Django's built-in logging for debugging

### Support

For issues and feature requests:
1. Check the logs for error messages
2. Review the configuration settings
3. Ensure all dependencies are installed correctly

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Django and Bootstrap
- Uses Chart.js for analytics visualization
- Bootstrap Icons for UI elements

## Version History

- **v1.0.0** - Initial release with core inventory management
- **v1.1.0** - Added dashboard and analytics features
- **v1.2.0** - Enhanced security and automated alerts

---

**Note**: This system is designed for pharmacy inventory management. Ensure compliance with local regulations and requirements for pharmaceutical record-keeping in your jurisdiction.