import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from tpm.models import Department, User, PillarEntry, KPIValue, Workstation, WorkstationKPI, WorkstationValue
from tpm.utils.kpi_definitions import KPI_DEFINITIONS
from tpm.utils.calculations import compute_achievement

class Command(BaseCommand):
    help = 'Seeds departments, users, and YTD sample actual data for demo purposes'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')

        # 1. Create Departments
        depts_data = [
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

        departments = {}
        for name, code in depts_data:
            dept, created = Department.objects.get_or_create(code=code, defaults={'name': name})
            departments[code] = dept

        self.stdout.write(f'Seeded {len(departments)} departments.')

        # 2. Create Admin User
        admin_pass = make_password('Admin@1234')
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@jspl.com',
                'first_name': 'TPM',
                'last_name': 'Administrator',
                'role': 'ADMIN',
                'password': admin_pass,
                'is_staff': True,
                'is_superuser': True
            }
        )
        if not created:
            admin.password = admin_pass
            admin.save()

        # 3. Create Department Users
        user_pass = make_password('Dept@1234')
        for code, dept in departments.items():
            username = code.lower()
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@jspl.com',
                    'first_name': dept.name,
                    'last_name': 'User',
                    'role': 'USER',
                    'department': dept,
                    'password': user_pass
                }
            )
            if not created:
                user.password = user_pass
                user.save()

        self.stdout.write('Seeded department users.')

        # 4. Seed Workstations for Plate Mill
        pm_dept = departments["PM"]
        ws1, _ = Workstation.objects.get_or_create(
            department=pm_dept, name='Furnace Area',
            defaults={'leader': 'D. Sao', 'inception_date': datetime.date(2025, 4, 1)}
        )
        ws2, _ = Workstation.objects.get_or_create(
            department=pm_dept, name='Mill Area',
            defaults={'leader': 'A. K. Sharma', 'inception_date': datetime.date(2025, 4, 1)}
        )

        kpi_ws1_1, _ = WorkstationKPI.objects.get_or_create(
            workstation=ws1, kpi_name='Break Down',
            defaults={'uom': 'Min/Month', 'goodness_indicator': 'LOWER', 'baseline': 177.0, 'commitment': 120.0}
        )
        kpi_ws1_2, _ = WorkstationKPI.objects.get_or_create(
            workstation=ws1, kpi_name='Fuel Consumption',
            defaults={'uom': 'MCAL/MT', 'goodness_indicator': 'LOWER', 'baseline': 421.0, 'commitment': 410.0}
        )
        kpi_ws2_1, _ = WorkstationKPI.objects.get_or_create(
            workstation=ws2, kpi_name='PRODUCTION',
            defaults={'uom': '%', 'goodness_indicator': 'HIGHER', 'baseline': 78.0, 'commitment': 85.0}
        )

        # 5. Seed sample monthly YTD data for PM (Plate Mill) and SMS2 (SMS-2)
        demo_depts = [pm_dept, departments["SMS2"]]
        today = datetime.date.today()
        current_year = today.year
        
        # Seed Jan to May
        for dept in demo_depts:
            for m in range(1, 6):
                # Standard Pillars Seed
                for p_code in ['KK', 'JH', 'PM', 'QM', 'ET', 'DM', 'SHE', 'OTPM']:
                    entry, _ = PillarEntry.objects.get_or_create(
                        department=dept, pillar=p_code, month=m, year=current_year
                    )
                    
                    # Lock earlier months, keep May unlocked as draft
                    if m < 5:
                        entry.submitted_at = datetime.datetime(current_year, m, 28, 17, 0)
                        entry.submitted_by = User.objects.filter(role='USER', department=dept).first() or admin
                        entry.save()
                        
                    definitions = KPI_DEFINITIONS.get(p_code, [])
                    for d in definitions:
                        # Generate some realistic mock actuals
                        tgt = d['target'] if d['target'] is not None else 10.0
                        
                        # Add variance
                        if d.get('is_PRODUCTION_row'):
                            avail = 92.0 - m
                            perf = 95.0 - (m * 0.5)
                            qual = 99.0 - (m * 0.1)
                            act = round((avail/100) * (perf/100) * (qual/100) * 100, 2)
                            KPIValue.objects.get_or_create(
                                pillar_entry=entry, sl_no=d['sl_no'],
                                defaults={
                                    'kpi_name': d['name'],
                                    'uom': d['uom'],
                                    'benchmark': d['benchmark'],
                                    'target': tgt,
                                    'availability': avail,
                                    'performance': perf,
                                    'quality': qual,
                                    'actual': act,
                                    'remarks': 'Calculated from subcomponents'
                                }
                            )
                        else:
                            # Standard actual
                            act = tgt
                            if act > 0:
                                act = round(tgt * (0.85 + (m * 0.03)), 1)
                            KPIValue.objects.get_or_create(
                                pillar_entry=entry, sl_no=d['sl_no'],
                                defaults={
                                    'kpi_name': d['name'],
                                    'uom': d['uom'],
                                    'benchmark': d['benchmark'],
                                    'target': tgt,
                                    'actual': act,
                                    'remarks': 'Auto seeded mock performance actual'
                                }
                            )

                # Workstation actuals seed (only for Plate Mill)
                if dept == pm_dept:
                    # ws1 kpis
                    v1, _ = WorkstationValue.objects.get_or_create(
                        workstation_kpi=kpi_ws1_1, month=m, year=current_year
                    )
                    v1.actual = round(150.0 - (m * 5.0), 1)
                    v1.remarks = 'Step improvements seen'
                    v1.save()
                    
                    v2, _ = WorkstationValue.objects.get_or_create(
                        workstation_kpi=kpi_ws1_2, month=m, year=current_year
                    )
                    v2.actual = round(418.0 - (m * 1.5), 1)
                    v2.save()

                    # ws2 kpi
                    v3, _ = WorkstationValue.objects.get_or_create(
                        workstation_kpi=kpi_ws2_1, month=m, year=current_year
                    )
                    v3.actual = round(80.0 + (m * 0.8), 1)
                    v3.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with demo data.'))
