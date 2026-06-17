import json
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from tpm.models import Department
from cmc.models import Equipment, PMScheduleEntry, SAPNotification, OilTestLog
from cmc.utils.status_logic import compute_overall_status, is_overdue
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')
def dept_overview(request, dept_id):
    today_date = date.today()
    
    if int(dept_id) == 0:
        class DummyDept:
            id = 0
            name = "Overall Plant"
            code = "Overall"
        department = DummyDept()
        
        # 1. Summary Ribbon Stats globally
        equipment_count = Equipment.objects.filter(is_active=True).count()
        
        monitored_this_month = PMScheduleEntry.objects.filter(
            actual_date__month=today_date.month,
            actual_date__year=today_date.year,
            status=PMScheduleEntry.VisitStatus.DONE
        ).count()

        due_today = PMScheduleEntry.objects.filter(
            scheduled_date=today_date,
            status=PMScheduleEntry.VisitStatus.PENDING
        ).count()

        open_notifications = SAPNotification.objects.filter(
            status=SAPNotification.NotifStatus.OPEN
        ).count()

        # 2. Equipment Health Board (Class A) globally
        class_a_equip = Equipment.objects.filter(
            equipment_class=Equipment.EquipmentClass.A,
            is_active=True
        ).prefetch_related('vibration_logs', 'oil_tests', 'wda_logs')
        
        health_board = []
        for eq in class_a_equip:
            last_vib = eq.vibration_logs.order_by('-date').first()
            last_oil = eq.oil_tests.order_by('-date').first()
            last_wda = eq.wda_logs.order_by('-date').first()
            
            health_board.append({
                'equipment': eq,
                'last_vibration': last_vib,
                'last_oil_test': last_oil,
                'last_wda': last_wda,
                'overall_status': compute_overall_status(last_vib, last_oil, last_wda),
            })

        # 3. Upcoming Schedule (Next 7 Days) globally
        end_date = today_date + timedelta(days=7)
        upcoming_entries = PMScheduleEntry.objects.filter(
            scheduled_date__range=(today_date, end_date),
            status=PMScheduleEntry.VisitStatus.PENDING
        ).order_by('scheduled_date')[:10]

        last_oil_test = OilTestLog.objects.all().order_by('-date').first()
        last_oil_status = last_oil_test.status if last_oil_test else 'N/A'
        
        # Department Summaries for overall dashboard
        all_depts = Department.objects.all().order_by('name')
        dept_summaries = []
        for d in all_depts:
            eqs = Equipment.objects.filter(department=d, is_active=True)
            if eqs.exists():
                eq_count = eqs.count()
                
                monitored = PMScheduleEntry.objects.filter(
                    equipment__department=d,
                    actual_date__month=today_date.month,
                    actual_date__year=today_date.year,
                    status=PMScheduleEntry.VisitStatus.DONE
                ).count()
                
                due = PMScheduleEntry.objects.filter(
                    equipment__department=d,
                    scheduled_date=today_date,
                    status=PMScheduleEntry.VisitStatus.PENDING
                ).count()
                
                open_notif = SAPNotification.objects.filter(
                    equipment__department=d,
                    status=SAPNotification.NotifStatus.OPEN
                ).count()
                
                last_oil = OilTestLog.objects.filter(equipment__department=d).order_by('-date').first()
                oil_status = last_oil.status if last_oil else 'N/A'
                
                dept_summaries.append({
                    'department': d,
                    'equipment_count': eq_count,
                    'monitored_this_month': monitored,
                    'due_today': due,
                    'open_notifications': open_notif,
                    'last_oil_status': oil_status,
                })
    else:
        dept_summaries = []
        department = get_object_or_404(Department, id=dept_id)
        
        # 1. Summary Ribbon Stats
        equipment_count = Equipment.objects.filter(department=department, is_active=True).count()
        
        monitored_this_month = PMScheduleEntry.objects.filter(
            equipment__department=department,
            actual_date__month=today_date.month,
            actual_date__year=today_date.year,
            status=PMScheduleEntry.VisitStatus.DONE
        ).count()

        due_today = PMScheduleEntry.objects.filter(
            equipment__department=department,
            scheduled_date=today_date,
            status=PMScheduleEntry.VisitStatus.PENDING
        ).count()

        open_notifications = SAPNotification.objects.filter(
            equipment__department=department,
            status=SAPNotification.NotifStatus.OPEN
        ).count()

        # 2. Equipment Health Board (Class A)
        class_a_equip = Equipment.objects.filter(
            department=department,
            equipment_class=Equipment.EquipmentClass.A,
            is_active=True
        ).prefetch_related('vibration_logs', 'oil_tests', 'wda_logs')
        
        health_board = []
        for eq in class_a_equip:
            last_vib = eq.vibration_logs.order_by('-date').first()
            last_oil = eq.oil_tests.order_by('-date').first()
            last_wda = eq.wda_logs.order_by('-date').first()
            
            health_board.append({
                'equipment': eq,
                'last_vibration': last_vib,
                'last_oil_test': last_oil,
                'last_wda': last_wda,
                'overall_status': compute_overall_status(last_vib, last_oil, last_wda),
            })

        # 3. Upcoming Schedule (Next 7 Days)
        end_date = today_date + timedelta(days=7)
        upcoming_entries = PMScheduleEntry.objects.filter(
            equipment__department=department,
            scheduled_date__range=(today_date, end_date),
            status=PMScheduleEntry.VisitStatus.PENDING
        ).order_by('scheduled_date')[:10]

        # Find the most recent oil test status for summary ribbon
        last_oil_test = OilTestLog.objects.filter(equipment__department=department).order_by('-date').first()
        last_oil_status = last_oil_test.status if last_oil_test else 'N/A'

    context = {
        'department': department,
        'monitored_this_month': monitored_this_month,
        'due_today': due_today,
        'open_notifications': open_notifications,
        'last_oil_status': last_oil_status,
        'health_board': health_board,
        'upcoming_entries': upcoming_entries,
        'dept_summaries': dept_summaries,
        'active_tab': 'overview',
    }
    return render(request, 'cmc/dashboard.html', context)

@login_required
@module_access_required('CMC')
def equipment_search(request):
    """HTMX: autocomplete equipment search across all departments"""
    q = request.GET.get('q', '').strip()
    dept_id = request.GET.get('dept_id')
    
    qs = Equipment.objects.filter(is_active=True)
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    if q:
        qs = qs.filter(name__icontains=q)[:10]
        
    return render(request, 'cmc/partials/_equipment_search.html', {'results': qs})
