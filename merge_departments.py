import os
import sys
import django
import argparse
from django.db import transaction
from django.apps import apps
from django.db.models import Q

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department, PillarEntry, KPIValue, CustomKPIDefinition, JHDepartmentSettings, User
from smed.models import SMEDTemplate
from portal.models import UserModuleAccess
from hod_kpi.models import HODKPIUpload, HODKPIMonthlySubmission
from delays.models import DelayDropdownOption, EquipmentShutdownSetting, ChecklistSchedule, PerformanceRecord, DelayNotification

DEPT_PAIRS = [
    # (src_code, src_name, tgt_code, tgt_name)
    ("BI", "BF - I", "BF1", "Blast Furnace-1"),
    ("BI1", "BF - II", "BF2", "Blast Furnace-2"),
    ("DI1", "DRI - I", "DRI1", "DRI-1"),
    ("DI", "DRI - II", "DRI2", "DRI-2"),
    ("PI", "PGP - II", "PGP2", "PGP-2"),
    ("PI1", "PGP - III", "PGP3", "PGP-3"),
    ("PPI3", "Power Plant - I", "PP1", "Power Plant 1"),
    ("PPI2", "Power Plant - II (Ph-1&2)", "PP2", "Power Plant 2"),
    ("PPI", "Power Plant - II (Ph. 3)", "PPP3", "Power Plant Phase #3"),
    ("PPI1", "Power Plant - III", "PP3", "Power Plant 3"),
    ("RMH1", "RMH - I", "RMHS1", "RMHS-1"),
    ("RMH3", "RMH - III", "RMHS3", "RMHS-3"),
]

def find_department(code, name):
    dept = Department.objects.filter(code__iexact=code).first()
    if dept:
        return dept
    dept = Department.objects.filter(name__iexact=name).first()
    if dept:
        return dept
    return None

def merge_departments(src, tgt, dry_run=True):
    print(f"\nConsolidating '{src.name}' ({src.code}) -> '{tgt.name}' ({tgt.code})...")
    
    # 1. UserModuleAccess
    access_src = UserModuleAccess.objects.filter(department=src)
    print(f"  - Found {access_src.count()} UserModuleAccess records")
    if not dry_run:
        for a_src in list(access_src):
            a_tgt = UserModuleAccess.objects.filter(user=a_src.user, department=tgt, module=a_src.module).first()
            if a_tgt:
                if a_src.access_level == 'EDIT' and a_tgt.access_level == 'VIEW':
                    a_tgt.access_level = 'EDIT'
                    a_tgt.save()
                a_src.delete()
            else:
                a_src.department = tgt
                a_src.save()

    # 2. PillarEntry
    pe_src_qs = PillarEntry.objects.filter(department=src)
    print(f"  - Found {pe_src_qs.count()} PillarEntry records")
    if not dry_run:
        for pe_src in list(pe_src_qs):
            pe_tgt, created = PillarEntry.objects.get_or_create(
                department=tgt,
                pillar=pe_src.pillar,
                month=pe_src.month,
                year=pe_src.year,
                defaults={'data_entry_type': pe_src.data_entry_type}
            )
            # Merge KPI values
            for kpi_src in list(KPIValue.objects.filter(pillar_entry=pe_src)):
                kpi_tgt = KPIValue.objects.filter(pillar_entry=pe_tgt, sl_no=kpi_src.sl_no).first()
                if kpi_tgt:
                    # Keep best values
                    if (kpi_tgt.actual is None or kpi_tgt.actual == 0.0) and kpi_src.actual is not None:
                        kpi_tgt.actual = kpi_src.actual
                    if kpi_tgt.target is None and kpi_src.target is not None:
                        kpi_tgt.target = kpi_src.target
                    if kpi_tgt.benchmark is None and kpi_src.benchmark is not None:
                        kpi_tgt.benchmark = kpi_src.benchmark
                    if kpi_tgt.availability is None and kpi_src.availability is not None:
                        kpi_tgt.availability = kpi_src.availability
                    if kpi_tgt.performance is None and kpi_src.performance is not None:
                        kpi_tgt.performance = kpi_src.performance
                    if kpi_tgt.quality is None and kpi_src.quality is not None:
                        kpi_tgt.quality = kpi_src.quality
                    if not kpi_tgt.remarks and kpi_src.remarks:
                        kpi_tgt.remarks = kpi_src.remarks
                    kpi_tgt.save()
                    kpi_src.delete()
                else:
                    kpi_src.pillar_entry = pe_tgt
                    kpi_src.save()
            
            # Submission merge
            if pe_src.submitted_at and not pe_tgt.submitted_at:
                pe_tgt.submitted_at = pe_src.submitted_at
                pe_tgt.submitted_by = pe_src.submitted_by
                pe_tgt.save()
            
            pe_src.delete()

    # 3. CustomKPIDefinition
    kpi_def_src = CustomKPIDefinition.objects.filter(department=src)
    print(f"  - Found {kpi_def_src.count()} CustomKPIDefinition records")
    if not dry_run:
        for c_src in list(kpi_def_src):
            c_tgt = CustomKPIDefinition.objects.filter(department=tgt, pillar=c_src.pillar, sl_no=c_src.sl_no).first()
            if c_tgt:
                c_src.delete()
            else:
                c_src.department = tgt
                c_src.save()

    # 4. JHDepartmentSettings
    jh_settings_src = JHDepartmentSettings.objects.filter(department=src)
    print(f"  - Found {jh_settings_src.count()} JHDepartmentSettings records")
    if not dry_run:
        for s_src in list(jh_settings_src):
            s_tgt = JHDepartmentSettings.objects.filter(department=tgt).first()
            if s_tgt:
                if (not s_tgt.hod_name or s_tgt.hod_name == "Mr. ") and s_src.hod_name:
                    s_tgt.hod_name = s_src.hod_name
                if (not s_tgt.coordinator_name or s_tgt.coordinator_name == "Mr. ") and s_src.coordinator_name:
                    s_tgt.coordinator_name = s_src.coordinator_name
                if not s_tgt.plan_start_date and s_src.plan_start_date:
                    s_tgt.plan_start_date = s_src.plan_start_date
                if not s_tgt.plan_end_date and s_src.plan_end_date:
                    s_tgt.plan_end_date = s_src.plan_end_date
                s_tgt.save()
                s_src.delete()
            else:
                s_src.department = tgt
                s_src.save()

    # 5. SMEDTemplate
    smed_src = SMEDTemplate.objects.filter(department=src)
    print(f"  - Found {smed_src.count()} SMEDTemplate records")
    if not dry_run:
        for t_src in list(smed_src):
            t_tgt = SMEDTemplate.objects.filter(department=tgt, code=t_src.code).first()
            if t_tgt:
                # Update runs
                for run_src in list(t_src.runs.all()):
                    run_tgt = t_tgt.runs.filter(date=run_src.date).first()
                    if run_tgt:
                        run_src.delete()
                    else:
                        run_src.template = t_tgt
                        run_src.save()
                t_src.delete()
            else:
                t_src.department = tgt
                t_src.save()

    # 6. HODKPIUpload
    upload_src = HODKPIUpload.objects.filter(department=src)
    print(f"  - Found {upload_src.count()} HODKPIUpload records")
    if not dry_run:
        for u_src in list(upload_src):
            u_tgt = HODKPIUpload.objects.filter(department=tgt, month=u_src.month, year=u_src.year).first()
            if u_tgt:
                # Merge records
                for r_src in list(u_src.records.all()):
                    r_tgt = u_tgt.records.filter(domain=r_src.domain, kpi_name=r_src.kpi_name, view_type=r_src.view_type).first()
                    if r_tgt:
                        if r_tgt.actual is None and r_src.actual is not None:
                            r_tgt.actual = r_src.actual
                            r_tgt.save()
                        r_src.delete()
                    else:
                        r_src.upload = u_tgt
                        r_src.save()
                # Merge delays
                for d_src in list(u_src.delays.all()):
                    d_tgt = u_tgt.delays.filter(reason=d_src.reason, duration_mins=d_src.duration_mins).first()
                    if d_tgt:
                        d_src.delete()
                    else:
                        d_src.upload = u_tgt
                        d_src.save()
                u_src.delete()
            else:
                u_src.department = tgt
                u_src.save()

    # 7. HODKPIMonthlySubmission
    sub_src = HODKPIMonthlySubmission.objects.filter(department=src)
    print(f"  - Found {sub_src.count()} HODKPIMonthlySubmission records")
    if not dry_run:
        for s_src in list(sub_src):
            s_tgt = HODKPIMonthlySubmission.objects.filter(department=tgt, month=s_src.month, year=s_src.year).first()
            if s_tgt:
                for field in ['achievements', 'risks', 'support_required', 'resources_required', 'special_observations', 'ai_summary', 'ai_recommendations']:
                    src_val = getattr(s_src, field, "").strip()
                    tgt_val = getattr(s_tgt, field, "").strip()
                    if src_val and src_val not in tgt_val:
                        setattr(s_tgt, field, f"{tgt_val}\n{src_val}".strip())
                s_tgt.save()
                s_src.delete()
            else:
                s_src.department = tgt
                s_src.save()

    # 8. DelayDropdownOption
    drop_src = DelayDropdownOption.objects.filter(department=src)
    print(f"  - Found {drop_src.count()} DelayDropdownOption records")
    if not dry_run:
        for o_src in list(drop_src):
            o_tgt = DelayDropdownOption.objects.filter(
                department=tgt, 
                category=o_src.category, 
                value=o_src.value, 
                parent_value=o_src.parent_value
            ).first()
            if o_tgt:
                o_src.delete()
            else:
                o_src.department = tgt
                o_src.save()

    # 9. EquipmentShutdownSetting
    shut_src = EquipmentShutdownSetting.objects.filter(department=src)
    print(f"  - Found {shut_src.count()} EquipmentShutdownSetting records")
    if not dry_run:
        for s_src in list(shut_src):
            s_tgt = EquipmentShutdownSetting.objects.filter(
                department=tgt,
                sub_area=s_src.sub_area,
                equipment=s_src.equipment
            ).first()
            if s_tgt:
                if s_src.shutdown_hrs > s_tgt.shutdown_hrs:
                    s_tgt.shutdown_hrs = s_src.shutdown_hrs
                    s_tgt.save()
                s_src.delete()
            else:
                s_src.department = tgt
                s_src.save()

    # 10. ChecklistSchedule
    sched_src = ChecklistSchedule.objects.filter(department=src)
    print(f"  - Found {sched_src.count()} ChecklistSchedule records")
    if not dry_run:
        for s_src in list(sched_src):
            s_tgt = ChecklistSchedule.objects.filter(
                department=tgt,
                checklist_name=s_src.checklist_name
            ).first()
            if s_tgt:
                if not s_tgt.assigned_hod and s_src.assigned_hod:
                    s_tgt.assigned_hod = s_src.assigned_hod
                    s_tgt.save()
                s_src.delete()
            else:
                s_src.department = tgt
                s_src.save()

    # 11. PerformanceRecord
    perf_src = PerformanceRecord.objects.filter(department=src)
    print(f"  - Found {perf_src.count()} PerformanceRecord records")
    if not dry_run:
        for r_src in list(perf_src):
            r_tgt = PerformanceRecord.objects.filter(department=tgt, date=r_src.date).first()
            if r_tgt:
                fields = [
                    'plan_tap_sms2', 'plan_prod_sms', 'plan_eaf2', 'plan_prod_eaf2',
                    'plan_neof', 'plan_prod_neof', 'actual_tap_sms2', 'actual_prod_sms',
                    'actual_eaf2', 'actual_prod_eaf2', 'actual_neof', 'actual_prod_neof',
                    'prod_loss_nof', 'prod_loss_eaf2', 'plan_eaf3_heats', 'plan_prod_eaf3',
                    'actual_eaf3_heats', 'actual_prod_eaf3', 'prod_loss_eaf3'
                ]
                for field in fields:
                    src_val = getattr(r_src, field, 0.0)
                    tgt_val = getattr(r_tgt, field, 0.0)
                    setattr(r_tgt, field, max(src_val, tgt_val))
                r_tgt.save()
                r_src.delete()
            else:
                r_src.department = tgt
                r_src.save()

    # 12. Special handle for DelayNotification
    notif_from_src = DelayNotification.objects.filter(from_department=src)
    notif_to_src = DelayNotification.objects.filter(to_department=src)
    print(f"  - Found {notif_from_src.count()} sent DelayNotifications and {notif_to_src.count()} received DelayNotifications")
    if not dry_run:
        notif_from_src.update(from_department=tgt)
        notif_to_src.update(to_department=tgt)

    # 13. Dynamic update for all other tables referencing Department
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, (django.db.models.ForeignKey, django.db.models.OneToOneField)):
                if field.related_model == Department:
                    # Ignore the ones we updated with custom logic where constraints existed
                    if model in [UserModuleAccess, PillarEntry, CustomKPIDefinition, JHDepartmentSettings, SMEDTemplate, HODKPIUpload, HODKPIMonthlySubmission, DelayDropdownOption, EquipmentShutdownSetting, ChecklistSchedule, PerformanceRecord, DelayNotification]:
                        continue
                    related_name = field.name
                    objs_count = model.objects.filter(**{related_name: src}).count()
                    if objs_count > 0:
                        print(f"  - Dynamic update required: {objs_count} records in {model.__name__} ({related_name})")
                        if not dry_run:
                            model.objects.filter(**{related_name: src}).update(**{related_name: tgt})

    # Finally, delete the source department
    if not dry_run:
        print(f"  - Deleting duplicate Department record '{src.name}' ({src.code})")
        src.delete()

def main():
    parser = argparse.ArgumentParser(description="Merge duplicate departments")
    parser.add_argument("--apply", action="store_true", help="Apply the consolidation to the database")
    args = parser.parse_args()
    
    dry_run = not args.apply
    if dry_run:
        print("=== DRY RUN MODE: PREVIEWING DATABASE CONSOLIDATION ===")
    else:
        print("=== APPLY MODE: MERGING DUPLICATE DEPARTMENTS IN DATABASE ===")
        
    with transaction.atomic():
        found_any = False
        for src_code, src_name, tgt_code, tgt_name in DEPT_PAIRS:
            src_dept = find_department(src_code, src_name)
            tgt_dept = find_department(tgt_code, tgt_name)
            
            if src_dept and tgt_dept:
                found_any = True
                merge_departments(src_dept, tgt_dept, dry_run=dry_run)
            elif src_dept and not tgt_dept:
                print(f"\nSource '{src_name}' ({src_code}) exists, but Target '{tgt_name}' ({tgt_code}) does not. Creating target first.")
                if not dry_run:
                    tgt_dept = Department.objects.create(name=tgt_name, code=tgt_code)
                    merge_departments(src_dept, tgt_dept, dry_run=dry_run)
            elif tgt_dept and not src_dept:
                # Target is already clean and duplicate doesn't exist
                pass
                
        if not found_any:
            print("\nNo active duplicate departments found to merge.")
            
        if dry_run:
            print("\nDry run completed. No database changes were saved.")
        else:
            print("\nConsolidation completed successfully! All changes committed.")

if __name__ == "__main__":
    main()
