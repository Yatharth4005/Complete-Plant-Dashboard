import os
import sys
import django
import openpyxl

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from django.db import transaction
from tpm.models import Department, PillarEntry, KPIValue

def to_float(val):
    if val is None or str(val).strip() == "" or str(val).strip().lower() in ['none', 'null', 'n/a', '-']:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def main():
    file_path = "PILLAR_MAPPING_MAPPED.xlsx"
    if not os.path.exists(file_path):
        print(f"Error: Could not find '{file_path}' in the current directory.")
        return

    print(f"Loading '{file_path}'...")
    wb = openpyxl.load_workbook(file_path, read_only=True)
    sheet = wb.active
    print(f"Reading sheet: '{sheet.title}'")

    rows = sheet.iter_rows(min_row=2, values_only=True)
    
    # Map for pillar names to choices
    PILLAR_MAP = {
        'E & T': 'ET',
        'EDUCATION': 'ET',
        'ET': 'ET',
        'KK': 'KK',
        'KOBETSU': 'KK',
        'JH': 'JH',
        'JISHU': 'JH',
        'PM': 'PM',
        'PLANNED': 'PM',
        'QM': 'QM',
        'QUALITY': 'QM',
        'DM': 'DM',
        'DESIGN': 'DM',
        'SHE': 'SHE',
        'SAFETY': 'SHE',
        'OTPM': 'OTPM',
        'OFFICE': 'OTPM'
    }

    count = 0
    skipped = 0
    
    print("Starting import inside database transaction...")
    with transaction.atomic():
        for row in rows:
            if not row or row[1] is None:  # DEPT_NAME is Col 1
                continue
                
            raw_dept_name = str(row[1]).strip()
            
            # Normalise SMS-2 and SMS-3 variants (including sub-areas) into SMS-2 and SMS-3
            dept_name_upper = raw_dept_name.upper()
            if 'SMS - II' in dept_name_upper or 'SMS-2' in dept_name_upper or dept_name_upper == 'SMS II' or dept_name_upper == 'SMS2':
                raw_dept_name = 'SMS-2'
            elif 'SMS - III' in dept_name_upper or 'SMS-3' in dept_name_upper or dept_name_upper == 'SMS III' or dept_name_upper == 'SMS3':
                raw_dept_name = 'SMS-3'

            raw_pillar_name = str(row[2]).strip()
            raw_entry_type = str(row[3]).strip() if row[3] is not None else 'M'
            year = int(row[4]) if row[4] is not None else None
            month = int(row[5]) if row[5] is not None else None
            
            benchmark = to_float(row[6])
            target = to_float(row[7])
            availability = to_float(row[8])
            performance = to_float(row[9])
            quality = to_float(row[10])
            actual = to_float(row[11])
            
            sl_no = str(row[13]).strip() if row[13] is not None else ''
            kpi_uom_str = str(row[14] or '').strip()

            if not raw_dept_name or not raw_pillar_name or not year or not month:
                skipped += 1
                continue

            # 1. Resolve Department
            dept = Department.objects.filter(name__iexact=raw_dept_name).first()
            if not dept:
                # Resolve code
                code = "".join([w[0].upper() for w in raw_dept_name.split() if w.isalnum()])[:10]
                if not code:
                    code = raw_dept_name[:3].upper()
                suffix = 1
                orig_code = code
                while Department.objects.filter(code=code).exists():
                    code = f"{orig_code[:8]}{suffix}"
                    suffix += 1
                dept = Department.objects.create(name=raw_dept_name, code=code)

            # 2. Resolve Pillar
            pillar_upper = raw_pillar_name.upper()
            pillar_code = None
            for key, val in PILLAR_MAP.items():
                if key in pillar_upper:
                    pillar_code = val
                    break
            if not pillar_code:
                pillar_code = pillar_upper[:4]

            # 3. Resolve Data Entry Type
            entry_type = 'WEEKLY' if raw_entry_type.upper().startswith('W') else 'MONTHLY'

            # 4. Resolve KPI Name and UOM
            kpi_name = kpi_uom_str
            uom = ""
            if ',' in kpi_uom_str:
                parts = kpi_uom_str.rsplit(',', 1)
                kpi_name = parts[0].strip()
                uom_part = parts[1].strip()
                if uom_part.startswith('(') and uom_part.endswith(')'):
                    uom = uom_part[1:-1].strip()
                else:
                    uom = uom_part
            elif ' (' in kpi_uom_str:
                parts = kpi_uom_str.rsplit(' (', 1)
                kpi_name = parts[0].strip()
                uom_part = parts[1].strip()
                if uom_part.endswith(')'):
                    uom = uom_part[:-1].strip()
                else:
                    uom = uom_part

            # 5. Get or Create PillarEntry
            pillar_entry, entry_created = PillarEntry.objects.get_or_create(
                department=dept,
                pillar=pillar_code,
                month=month,
                year=year,
                defaults={
                    'data_entry_type': entry_type
                }
            )

            # 6. Create or Update KPIValue (avoiding overwriting valid data with nulls)
            kpi_val = KPIValue.objects.filter(pillar_entry=pillar_entry, sl_no=sl_no).first()
            if kpi_val:
                # Merge data: only overwrite fields if the incoming Excel row has a non-Null value
                if benchmark is not None: kpi_val.benchmark = benchmark
                if target is not None: kpi_val.target = target
                if actual is not None: kpi_val.actual = actual
                if availability is not None: kpi_val.availability = availability
                if performance is not None: kpi_val.performance = performance
                if quality is not None: kpi_val.quality = quality
                if kpi_name: kpi_val.kpi_name = kpi_name
                if uom: kpi_val.uom = uom
                kpi_val.save()
            else:
                KPIValue.objects.create(
                    pillar_entry=pillar_entry,
                    sl_no=sl_no,
                    kpi_name=kpi_name,
                    uom=uom,
                    benchmark=benchmark,
                    target=target,
                    actual=actual,
                    availability=availability,
                    performance=performance,
                    quality=quality
                )

            count += 1
            if count % 1000 == 0:
                print(f"Processed {count} rows...")

    print(f"\nFinished! Seeded/Updated {count} KPI rows (skipped {skipped}).")

if __name__ == '__main__':
    main()
