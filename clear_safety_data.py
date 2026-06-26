import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from Safety.models import Incident

# Delete all Incident records
count, _ = Incident.objects.all().delete()
print(f"Successfully deleted {count} safety incidents from the database.")
