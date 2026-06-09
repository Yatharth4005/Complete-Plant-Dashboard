from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from tpm.models import User, Department
from portal.models import Module, UserModuleAccess

class Command(BaseCommand):
    help = 'Seed initial portal registries: departments, modules, and default role accesses'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding portal database...')
        self.seed_departments()
        self.seed_modules()
        self.seed_portal_users_and_access()
        self.stdout.write(self.style.SUCCESS('Portal seed completed successfully.'))

    def seed_departments(self):
        DEPARTMENTS = [
            ("Blast Furnace-1", "BF1"),
            ("Blast Furnace-2", "BF2"),
            ("Brick Plant", "BP"),
            ("Cement Plant", "CP"),
            ("Coke Oven", "CO"),
            ("DRI-1", "DRI1"),
            ("DRI-2", "DRI2"),
            ("Extrusion Plant", "EP"),
            ("Lime and Dolo Plant", "LDP"),
            ("Oxygen Plant", "OP"),
            ("PGP-1", "PGP1"),
            ("PGP-2", "PGP2"),
            ("PGP-3", "PGP3"),
            ("Plate Mill", "PM"),
            ("Power Plant 1", "PP1"),
            ("Power Plant 2", "PP2"),
            ("Power Plant 3", "PP3"),
            ("Power Plant Phase #3", "PPP3"),
            ("RMHS-1", "RMHS1"),
            ("RMHS-2", "RMHS2"),
            ("RMHS-3", "RMHS3"),
            ("Rail Mill", "RM"),
            ("SAF-1", "SAF1"),
            ("SAF-2", "SAF2"),
            ("SMS-2", "SMS2"),
            ("SMS-3", "SMS3"),
            ("Sinter", "SINT"),
            ("Special Profile Mill (SPM)", "SPM"),
        ]
        
        for name, code in DEPARTMENTS:
            Department.objects.get_or_create(code=code, defaults={'name': name})
            
        self.stdout.write(f'  [OK] Seeded {len(DEPARTMENTS)} plant departments.')

    def seed_modules(self):
        # Clean up old deprecated modules
        Module.objects.filter(key__in=['PRODUCTION', 'SAFETY', 'HR']).delete()

        MODULES = [
            {
                'key': 'TPM',
                'label': 'Total Productive Maintenance',
                'description': 'KPI tracking across 8 pillars + Workstation KPIs',
                'icon': 'gear',
                'color_class': 'module-tpm',
                'redirect_url_template': 'http://localhost:8001/department/{dept_id}/',
                'sort_order': 1,
            },
            {
                'key': 'CMC',
                'label': 'Condition Monitoring Cell',
                'description': 'Machinery health: vibration monitoring, oil testing, and wear debris analysis (WDA)',
                'icon': 'file-contract',
                'color_class': 'module-cmc',
                'redirect_url_template': 'http://localhost:8002/department/{dept_id}/',
                'sort_order': 2,
            },
            {
                'key': 'ISO',
                'label': 'ISO Compliance & Standards',
                'description': 'Standard operating procedures, internal audit compliance logs',
                'icon': 'award',
                'color_class': 'module-iso',
                'redirect_url_template': '/department/{dept_id}/coming-soon/ISO/',
                'sort_order': 3,
            },
            {
                'key': 'Delays',
                'label': 'Delay Logs & Tracking',
                'description': 'Production line downtime, log summaries, and breakdown analysis',
                'icon': 'clock',
                'color_class': 'module-delays',
                'redirect_url_template': '/department/{dept_id}/coming-soon/delays/',
                'sort_order': 4,
            },
            {
                'key': 'OEE',
                'label': 'Overall Equipment Effectiveness',
                'description': 'Equipment performance, availability, and quality metrics',
                'icon': 'bar-chart',
                'color_class': 'module-oee',
                'redirect_url_template': '/department/{dept_id}/coming-soon/oee/',
                'sort_order': 5,
            },
            {
                'key': 'Availability',
                'label': 'Availability Logs',
                'description': 'Uptime monitoring, machine availability logs, and maintenance alerts',
                'icon': 'activity',
                'color_class': 'module-availability',
                'redirect_url_template': '/department/{dept_id}/coming-soon/availability/',
                'sort_order': 6,
            },
        ]
        
        for m in MODULES:
            Module.objects.update_or_create(key=m['key'], defaults=m)
            
        self.stdout.write(f'  [OK] Seeded {len(MODULES)} operational modules.')

    def seed_portal_users_and_access(self):
        # 1. Update/Create Saurabh Agrawal as Plant Admin
        admin_pass = make_password('Admin@1234')
        admin, created = User.objects.update_or_create(
            username='saurabh.agrawal@jindalsteel.in',
            defaults={
                'email': 'saurabh.agrawal@jindalsteel.in',
                'first_name': 'Saurabh',
                'last_name': 'Agrawal',
                'role': User.ROLE_ADMIN,
                'is_plant_admin': True,
                'is_staff': True,
                'is_superuser': True,
                'password': admin_pass,
            }
        )
        self.stdout.write('  [OK] Seeded Plant Admin: saurabh.agrawal@jindalsteel.in')

        # 2. Update/Create Lalit Goyal as SMS-2 user
        sms2_dept = Department.objects.get(code='SMS2')
        user_pass = make_password('Dept@1234')
        lalit, created = User.objects.update_or_create(
            username='lalit.goyal@jindalsteel.in',
            defaults={
                'email': 'lalit.goyal@jindalsteel.in',
                'first_name': 'Lalit',
                'last_name': 'Goyal',
                'role': User.ROLE_USER,
                'department': sms2_dept,
                'password': user_pass,
            }
        )
        self.stdout.write('  [OK] Seeded Department User: lalit.goyal@jindalsteel.in')

        # Grant Lalit TPM and CMC access inside SMS-2 for testing
        tpm_mod = Module.objects.get(key='TPM')
        cmc_mod = Module.objects.get(key='CMC')
        
        UserModuleAccess.objects.get_or_create(
            user=lalit,
            department=sms2_dept,
            module=tpm_mod,
            defaults={'access_level': 'EDIT', 'granted_by': admin}
        )
        UserModuleAccess.objects.get_or_create(
            user=lalit,
            department=sms2_dept,
            module=cmc_mod,
            defaults={'access_level': 'VIEW', 'granted_by': admin}
        )
        self.stdout.write('  [OK] Seeded module access permissions for Lalit Goyal (SMS-2).')
