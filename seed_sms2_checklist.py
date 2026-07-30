import os
import sys
import django
import xlrd

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department
from delays.models import DelayDropdownOption, MaintenanceChecklist, ChecklistSchedule

def seed_sms2_checklist():
    dept_code = "SMS2"
    excel_path = r"E:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\SMS2 CHECK LIST CRANE PREVENTIVE MAINTENANCE.xls"
    if not os.path.exists(excel_path):
        excel_path = "SMS2 CHECK LIST CRANE PREVENTIVE MAINTENANCE.xls"
        
    if not os.path.exists(excel_path):
        print(f"File not found at: {excel_path}")
        return
        
    print("Opening Excel workbook...")
    wb = xlrd.open_workbook(excel_path)
    sheet = wb.sheet_by_index(0)
    
    # Find the SMS2 department in the DB
    target_dept = (
        Department.objects.filter(code__iexact="SMS2").first() or 
        Department.objects.filter(code__iexact="SMS-2").first() or 
        Department.objects.filter(name__icontains="SMS2").first() or 
        Department.objects.filter(name__icontains="SMS-2").first()
    )
    if not target_dept:
        print(f"Department '{dept_code}' not found in database!")
        return
        
    print(f"Found Department: {target_dept.name} ({target_dept.code})")
    
    # 1. Ensure 'Maintenance' is registered as Area (Sub-Agency) for checklists
    area_opt, created = DelayDropdownOption.objects.get_or_create(
        department=target_dept,
        category='Sub-Agency',
        value='Maintenance'
    )
    if created:
        print("Registered Sub-Agency Area: Maintenance")
    else:
        print("Verified Sub-Agency Area: Maintenance")
        
    checklist_name = "EOT Cranes"
    
    # 2. Register/Verify checklist name under 'Maintenance'
    checklist_opt, created = DelayDropdownOption.objects.get_or_create(
        department=target_dept,
        category='Equipment',
        value=checklist_name,
        parent_value='Maintenance'
    )
    if created:
        print(f"Registered Checklist Equipment: {checklist_name}")
    else:
        print(f"Verified Checklist Equipment: {checklist_name}")

    # 3. Clear existing action options for this checklist to avoid duplicates/scrambling
    deleted_opts = DelayDropdownOption.objects.filter(
        department=target_dept,
        category='Action',
        parent_value=checklist_name
    ).delete()
    print(f"Cleared {deleted_opts[0]} existing action options for checklist: {checklist_name}")

    # Define helper to seed Option
    def seed_action(value, is_header=False):
        opt, created = DelayDropdownOption.objects.update_or_create(
            department=target_dept,
            category='Action',
            value=value[:255],  # max_length safety
            parent_value=checklist_name,
            defaults={'is_header': is_header}
        )
        if created:
            print(f"  [+] Created Action: '{value}' (Header: {is_header})")

    current_section = None
    
    # Iterate through rows
    for r in range(sheet.nrows):
        sr_no_val = str(sheet.cell_value(r, 0)).strip()
        item_val = str(sheet.cell_value(r, 1)).strip()
        
        # Clean up Excel decimal floats in SR.NO. (e.g. "1.0" -> "1")
        if sr_no_val.endswith('.0'):
            sr_no_val = sr_no_val[:-2]
            
        if not item_val or item_val.upper() in ('ITEM TO BE CHECKED', 'STATUS', 'REMARK', 'SR.NO.', 'SR. NO.'):
            continue
            
        # Check if it's a section header
        if not sr_no_val or sr_no_val == '-':
            header_name = item_val.strip()
            if header_name:
                # Filter out signature labels
                hn_upper = header_name.upper()
                if any(x in hn_upper for x in ('CHECKED BY', 'SIGNATURE', 'IN-CHARGE', 'INCHARGE', 'SHIFT INCHARGE')):
                    continue
                current_section = header_name
                seed_action(current_section, is_header=True)
        else:
            # Check if sr_no_val is a number
            is_num = False
            try:
                float(sr_no_val)
                is_num = True
            except ValueError:
                pass
                
            if is_num and current_section and item_val:
                action_val = f"{current_section} - {item_val.strip()}"
                seed_action(action_val, is_header=False)
                
    # 4. Register ChecklistSchedule for EOT Cranes with Daily frequency if not exists
    sched, created = ChecklistSchedule.objects.get_or_create(
        department=target_dept,
        checklist_name=checklist_name,
        defaults={'frequency': 'Daily'}
    )
    if created:
        print(f"Created ChecklistSchedule for: {checklist_name}")
    else:
        print(f"Verified ChecklistSchedule for: {checklist_name}")

    print("\nSMS-2 EOT Cranes checklist seeding completed successfully!")

if __name__ == "__main__":
    seed_sms2_checklist()
