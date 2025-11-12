"""
Management command to check for expiring medicines and low stock alerts
Run this daily via cron job: python manage.py check_alerts
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from datetime import timedelta
from inventory.models import MedicineInventory, StockAlert
import logging

logger = logging.getLogger('inventory')


class Command(BaseCommand):
    help = 'Check for expiring medicines and low stock, create alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send email notifications for critical alerts',
        )
        parser.add_argument(
            '--clean-old-alerts',
            action='store_true',
            help='Clean up old acknowledged alerts',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting inventory alert check...')
        
        alerts_created = 0
        
        # Check for expired medicines
        today = timezone.now().date()
        expired_items = MedicineInventory.objects.filter(expiry_date__lte=today)
        
        for item in expired_items:
            alert, created = StockAlert.objects.get_or_create(
                medicine_name=item.medicine_name,
                alert_type='expired',
                defaults={
                    'message': f'{item.medicine_name} (Batch: {item.batch_no}) has expired on {item.expiry_date}'
                }
            )
            if created:
                alerts_created += 1
                logger.warning(f'Expired medicine alert: {item.medicine_name} (Batch: {item.batch_no})')

        # Check for medicines expiring soon
        expiry_threshold = today + timedelta(days=getattr(settings, 'EXPIRY_ALERT_DAYS', 30))
        expiring_items = MedicineInventory.objects.filter(
            expiry_date__gt=today,
            expiry_date__lte=expiry_threshold
        )
        
        for item in expiring_items:
            alert, created = StockAlert.objects.get_or_create(
                medicine_name=item.medicine_name,
                alert_type='near_expiry',
                defaults={
                    'message': f'{item.medicine_name} (Batch: {item.batch_no}) expires in {item.days_to_expiry} days'
                }
            )
            if created:
                alerts_created += 1
                logger.info(f'Near expiry alert: {item.medicine_name} (Batch: {item.batch_no})')

        # Check for low stock
        for item in MedicineInventory.objects.all():
            if item.is_low_stock:
                alert, created = StockAlert.objects.get_or_create(
                    medicine_name=item.medicine_name,
                    alert_type='low_stock',
                    defaults={
                        'message': f'Low stock alert: {item.medicine_name} (Current balance: {item.balance()})'
                    }
                )
                if created:
                    alerts_created += 1
                    logger.warning(f'Low stock alert: {item.medicine_name} (Balance: {item.balance()})')

        # Send email notifications if requested
        if options['send_email'] and alerts_created > 0:
            self.send_alert_emails()

        # Clean old alerts if requested
        if options['clean_old_alerts']:
            old_alerts = StockAlert.objects.filter(
                is_acknowledged=True,
                acknowledged_at__lte=timezone.now() - timedelta(days=30)
            )
            deleted_count = old_alerts.count()
            old_alerts.delete()
            self.stdout.write(f'Cleaned up {deleted_count} old alerts')

        self.stdout.write(
            self.style.SUCCESS(f'Alert check completed. Created {alerts_created} new alerts.')
        )

    def send_alert_emails(self):
        """Send email notifications for critical alerts"""
        try:
            critical_alerts = StockAlert.objects.filter(
                is_acknowledged=False,
                alert_type__in=['expired', 'low_stock']
            )
            
            if not critical_alerts.exists():
                return

            message_lines = ['Critical Pharmacy Inventory Alerts:', '']
            
            for alert in critical_alerts:
                message_lines.append(f'• {alert.get_alert_type_display()}: {alert.message}')
            
            message_lines.extend([
                '',
                'Please log in to the pharmacy system to review and address these alerts.',
                f'System: {settings.PHARMACY_NAME}',
            ])

            send_mail(
                subject='Critical Pharmacy Inventory Alerts',
                message='\n'.join(message_lines),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],  # You might want to configure a separate admin email list
                fail_silently=False,
            )
            
            logger.info(f'Alert email sent for {critical_alerts.count()} critical alerts')
            self.stdout.write('Alert email sent successfully')
            
        except Exception as e:
            logger.error(f'Failed to send alert email: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Failed to send alert email: {str(e)}'))