from django.core.management.base import BaseCommand
from portal.models import Module, UserModuleAccess
from tpm.models import Department, User

class Command(BaseCommand):
    help = 'Seeds HOD KPI Review module and configures default department user access.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding HOD KPI Review Module...')
        
        # 1. Create or update the Module
        module, created = Module.objects.update_or_create(
            key='HOD_KPI',
            defaults={
                'label': 'HOD KPI Review',
                'description': 'HOD KPI monthly performance review and narrative submission.',
                'icon': 'chart-bar',
                'color_class': 'module-hod-kpi',
                'redirect_url_template': '/hod-kpi/dashboard/?department_id={dept_id}',
                'is_active': True,
                'sort_order': 10
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created module: {module.label}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated module: {module.label}"))
            
        # 2. Grant access to all active users for their respective departments
        users = User.objects.filter(is_active=True, department__isnull=False)
        access_count = 0
        
        for user in users:
            access, created = UserModuleAccess.objects.get_or_create(
                user=user,
                department=user.department,
                module=module,
                defaults={
                    'access_level': UserModuleAccess.AccessLevel.EDIT
                }
            )
            if created:
                access_count += 1
                
        self.stdout.write(self.style.SUCCESS(f"Granted KPI module access to {access_count} users."))
        self.stdout.write(self.style.SUCCESS("HOD KPI Module seeding completed successfully!"))
