#!/bin/bash

# Pharmacy Inventory Tracker - Deployment Script

set -e

echo "🚀 Starting Pharmacy Inventory Tracker Deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    print_error "manage.py not found. Please run this script from the pharmacy_inventory directory."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv .venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your production settings before continuing."
        read -p "Press enter to continue after editing .env file..."
    else
        print_error ".env.example not found. Please create .env file manually."
        exit 1
    fi
fi

# Run migrations
print_status "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if none exists
print_status "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Please create one:')
    exit(1)
else:
    print('Superuser already exists.')
" || {
    print_warning "Creating superuser..."
    python manage.py createsuperuser
}

# Generate secret key if needed
python manage.py shell -c "
from django.core.management.utils import get_random_secret_key
print('Random secret key for production:', get_random_secret_key())
"

print_status "✅ Deployment preparation complete!"
echo
echo "📋 Next Steps:"
echo "1. Update .env file with production settings"
echo "2. Set DEBUG=False in production"
echo "3. Update ALLOWED_HOSTS with your domain"
echo "4. Configure database for production (PostgreSQL recommended)"
echo "5. Set up web server (Nginx + Gunicorn)"
echo
echo "🐳 For Docker deployment:"
echo "   docker-compose up -d"
echo
echo "☁️ For Heroku deployment:"
echo "   git add . && git commit -m 'Production ready'"
echo "   heroku create your-app-name"
echo "   git push heroku main"
echo
print_status "🎉 Your Pharmacy Inventory Tracker is ready for deployment!"