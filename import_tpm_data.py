import os
import django
import openpyxl

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department, PillarEntry, KPIValue

# Configuration
EXCEL_FILE = r"e:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\PILLAR_MAPPING_MAPPED.xlsx"

EXPLICIT_DEPT_MAPPING = {
    'BF - I': 'Blast Furnace-1',
    'BF - II': 'Blast Furnace-2',
    'Cement Plant': 'Cement Plant',
    'Coke Oven': 'Coke Oven',
    'DRI - I': 'DRI-1',
    'DRI - II': 'DRI-2',
    'Lime & Dolo Plant': 'Lime and Dolo Plant',
    'Oxygen Plant': 'Oxygen Plant',
    'PGP - II': 'PGP-2',
    'PGP - III': 'PGP-3',
    'Plate Mill': 'Plate Mill',
    'Power Plant - I': 'Power Plant 1',
    'Power Plant - II (Ph-1&2)': 'Power Plant 2',
    'Power Plant - II (Ph. 3)': 'Power Plant Phase #3',
    'Power Plant - III': 'Power Plant 3',
    'RMH - I': 'RMHS-1',
    'RMH - III': 'RMHS-3',
    'RAIL MILL': 'Rail Mill',
    'SMS - II': 'SMS-2',
    'SMS - III': 'SMS-3',
    'SMS - II/BILLET CASTER': 'SMS-2',
    'SMS - II/COMBI CASTER': 'SMS-2',
    'SMS - II/EAF': 'SMS-2',
    'SMS - II/NOF': 'SMS-2',
    'SMS - II/SLAB CASTER': 'SMS-2',
    'SMS - III/BILLET CASTER': 'SMS-3',
    'SMS - III/COMBI CASTER': 'SMS-3',
    'Sinter Plant': 'Sinter',
    'SPM': 'Special Profile Mill (SPM)',
}

PILLAR_MAP = {
    'DM': 'DM',
    'E & T': 'ET',
    'JH': 'JH',
    'KK': 'KK',
    'OTPM': 'OTPM',
    'PM': 'PM',
    'QM': 'QM',
    'SHE': 'SHE'
}

def generate_dept_code(name):
    # Remove special characters
    clean_name = "".join(c for c in name if c.isalnum() or c.isspace()).strip()
    words = clean_name.split()
    if len(words) == 1:
        return words[0][:4].upper()
    else:
        return "".join(w[0] for w in words).upper()[:5]

def parse_kpi_uom(kpi_uom):
    if not kpi_uom:
        return "", ""
    kpi_uom = str(kpi_uom).strip()
    if ', ' in kpi_uom:
        parts = kpi_uom.rsplit(', ', 1)
        name, uom = parts[0].strip(), parts[1].strip()
    elif ',' in kpi_uom:
        parts = kpi_uom.rsplit(',', 1)
        name, uom = parts[0].strip(), parts[1].strip()
    else:
        name, uom = kpi_uom, ""
    
    if uom.startswith('(') and uom.endswith(')'):
        uom = uom[1:-1].strip()
    return name, uom

def to_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def import_tpm_data():
    print(f"Loading Excel file: {EXCEL_FILE}")
    wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True)
    sheet = wb.active
    print(f"Active Sheet: {sheet.title}")

    # 1. Fetch/Initialize Department mapping cache
    print("Caching existing departments...")
    db_depts = {d.name.strip().lower(): d for d in Department.objects.all()}
    db_depts_by_code = {d.code.strip().lower(): d for d in Department.objects.all()}

    def get_or_create_dept(raw_name):
        raw_name_strip = str(raw_name).strip()
        mapped_name = EXPLICIT_DEPT_MAPPING.get(raw_name_strip, raw_name_strip)
        
        # Check by mapped name
        key = mapped_name.lower()
        if key in db_depts:
            return db_depts[key]
        
        # Check by raw name
        key_raw = raw_name_strip.lower()
        if key_raw in db_depts:
            return db_depts[key_raw]

        # Create new department
        code = generate_dept_code(mapped_name)
        # Ensure code is unique in our cache/db
        base_code = code
        counter = 1
        while code.lower() in db_depts_by_code:
            code = f"{base_code}{counter}"
            counter += 1

        print(f"Creating new department: '{mapped_name}' with Code: '{code}' (parsed from Excel: '{raw_name_strip}')")
        dept = Department.objects.create(name=mapped_name, code=code)
        db_depts[mapped_name.lower()] = dept
        db_depts_by_code[code.lower()] = dept
        return dept

    # 2. First pass: load Excel rows and group entries
    print("Reading and grouping Excel rows...")
    row_count = 0
    grouped_rows = {} # Key: (dept_id, pillar_code, month, year) -> list of row dicts

    for idx, row in enumerate(sheet.iter_rows(min_row=2, max_row=300000, values_only=True)):
        if not row or not any(row):
            continue
        
        row_count += 1
        raw_dept = row[1]
        raw_pillar = row[2]
        year = to_float(row[4])
        month = to_float(row[5])

        if not raw_dept or not raw_pillar or not year or not month:
            continue

        year = int(year)
        month = int(month)
        
        pillar_code = PILLAR_MAP.get(str(raw_pillar).strip(), str(raw_pillar).strip())
        dept_obj = get_or_create_dept(raw_dept)
        
        group_key = (dept_obj.id, pillar_code, month, year)
        if group_key not in grouped_rows:
            grouped_rows[group_key] = []
        
        grouped_rows[group_key].append(row)

        if row_count % 50000 == 0:
            print(f"Read {row_count} rows...")

    print(f"Finished reading {row_count} rows. Grouped into {len(grouped_rows)} unique database pillar entries.")

    # 3. Create Pillar Entries that do not exist yet
    print("Syncing Pillar Entries...")
    existing_pillar_entries = {}
    for pe in PillarEntry.objects.all():
        key = (pe.department_id, pe.pillar, pe.month, pe.year)
        existing_pillar_entries[key] = pe

    new_pillar_entries = []
    for key, rows in grouped_rows.items():
        if key not in existing_pillar_entries:
            # Determine data_entry_type: 'WEEKLY' only if all rows in the group say 'W', else default to 'MONTHLY'
            has_weekly = any(row[3] == 'W' for row in rows)
            has_monthly = any(row[3] == 'M' or row[3] is None for row in rows)
            entry_type = 'WEEKLY' if (has_weekly and not has_monthly) else 'MONTHLY'
            
            new_pillar_entries.append(
                PillarEntry(
                    department_id=key[0],
                    pillar=key[1],
                    month=key[2],
                    year=key[3],
                    data_entry_type=entry_type
                )
            )

    if new_pillar_entries:
        print(f"Bulk creating {len(new_pillar_entries)} new PillarEntry records...")
        PillarEntry.objects.bulk_create(new_pillar_entries)
        # Re-fetch all to get their IDs
        existing_pillar_entries = {}
        for pe in PillarEntry.objects.all():
            key = (pe.department_id, pe.pillar, pe.month, pe.year)
            existing_pillar_entries[key] = pe
        print("PillarEntry records synced successfully.")

    # 4. Delete old KPI values for the entries we are importing to prevent duplicates
    print("Deleting old KPIValue records for affected entries...")
    affected_entry_ids = [existing_pillar_entries[key].id for key in grouped_rows.keys()]
    
    # We delete in batches to prevent hitting SQL query parameters limit
    batch_size = 5000
    for i in range(0, len(affected_entry_ids), batch_size):
        batch_ids = affected_entry_ids[i:i+batch_size]
        KPIValue.objects.filter(pillar_entry_id__in=batch_ids).delete()
    print("Old KPIValue records cleared.")

    # 5. Populate and bulk create KPI Values
    print("Compiling KPIValue records...")
    kpi_values_to_create = {} # Key: (pillar_entry_id, sl_no) -> KPIValue obj

    for key, rows in grouped_rows.items():
        pe = existing_pillar_entries[key]
        for row in rows:
            sl_no = str(row[13] if row[13] is not None else '').strip()
            if not sl_no:
                continue

            kpi_name, uom = parse_kpi_uom(row[14])
            benchmark = to_float(row[6])
            target = to_float(row[7])
            avail = to_float(row[8])
            perf = to_float(row[9])
            qual = to_float(row[10])
            actual = to_float(row[11])

            kpi_val = KPIValue(
                pillar_entry=pe,
                sl_no=sl_no,
                kpi_name=kpi_name,
                uom=uom,
                benchmark=benchmark,
                target=target,
                actual=actual,
                availability=avail,
                performance=perf,
                quality=qual
            )
            
            # Deduplicate locally (keep the last occurrence in case of Excel row duplicates)
            kpi_key = (pe.id, sl_no)
            kpi_values_to_create[kpi_key] = kpi_val

    kpi_list = list(kpi_values_to_create.values())
    print(f"Bulk creating {len(kpi_list)} KPIValue records in batches...")
    
    # Insert in batches of 10000 for maximum performance
    for i in range(0, len(kpi_list), 10000):
        batch = kpi_list[i:i+10000]
        KPIValue.objects.bulk_create(batch)
        print(f"Inserted {i + len(batch)} / {len(kpi_list)} records...")

    print("\nIMPORT COMPLETED SUCCESSFULLY!")
    print(f"Total Rows Processed: {row_count}")
    print(f"Total Pillar Entries Updated/Created: {len(grouped_rows)}")
    print(f"Total KPI Values Inserted: {len(kpi_list)}")

if __name__ == '__main__':
    import_tpm_data()
