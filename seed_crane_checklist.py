import os
import sys
import django
import xlrd

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department
from delays.models import DelayDropdownOption

def seed_crane_checklist():
    dept_code = sys.argv[1] if len(sys.argv) > 1 else "SMS2"
    excel_path = r"E:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\SMS2 CHECK LIST CRANE PREVENTIVE MAINTENANCE.xls"
    if not os.path.exists(excel_path):
        print(f"File not found at: {excel_path}")
        return
        
    print("Opening Excel workbook...")
    wb = xlrd.open_workbook(excel_path)
    
    # Find the target department in the DB
    target_dept = Department.objects.filter(code__iexact=dept_code).first() or Department.objects.filter(name__icontains=dept_code).first()
    if not target_dept:
        print(f"Department '{dept_code}' not found in database!")
        return
        
    print(f"Found Department: {target_dept.name} ({target_dept.code})")
    
    # Ensure 'Crane' is registered as Area (Sub-Agency) for this department
    area_opt, _ = DelayDropdownOption.objects.get_or_create(
        department=target_dept,
        category='Sub-Agency',
        value='Crane'
    )
    print("Registered/verified Area: Crane")

    # Iterate through sheets
    for sheet_idx in range(wb.nsheets):
        sheet = wb.sheet_by_index(sheet_idx)
        print(f"Processing sheet: {sheet.name}")
        
        current_equipment = None
        
        # Start reading from row 0 to the end
        for r_idx in range(sheet.nrows):
            sr_no_val = str(sheet.cell_value(r_idx, 0)).strip()
            item_val = str(sheet.cell_value(r_idx, 1)).strip()
            
            # Clean up Excel decimal floats in SR.NO. (e.g. "1.0" -> "1")
            if sr_no_val.endswith('.0'):
                sr_no_val = sr_no_val[:-2]
                
            if not item_val or item_val.upper() in ('ITEM TO BE CHECKED', 'STATUS', 'REMARK', 'SR.NO.', 'SR. NO.'):
                continue
                
            # If SR.NO. is empty, this is an Equipment header
            if not sr_no_val or sr_no_val == '-':
                eq_name = item_val.upper().strip()
                if eq_name:
                    current_equipment = eq_name
                    # Seed the Equipment under parent 'Crane'
                    DelayDropdownOption.objects.get_or_create(
                        department=target_dept,
                        category='Equipment',
                        value=current_equipment,
                        parent_value='Crane'
                    )
                    print(f"  └─ Equipment: {current_equipment}")
            else:
                # This is an Action under the current equipment
                if current_equipment and item_val:
                    action_val = item_val.strip()
                    # Seed the Action option linked to the parent equipment
                    DelayDropdownOption.objects.get_or_create(
                        department=target_dept,
                        category='Action',
                        value=action_val,
                        parent_value=current_equipment
                    )
                    # Also seed standard Action without parent value
                    DelayDropdownOption.objects.get_or_create(
                        department=target_dept,
                        category='Action',
                        value=action_val,
                        parent_value=None
                    )

    print("Crane checklist seeding completed successfully!")

if __name__ == "__main__":
    seed_crane_checklist()
