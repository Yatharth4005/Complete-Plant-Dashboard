import os
import re
import xlrd
import openpyxl
from datetime import datetime, date
from django.db import transaction
from django.utils import timezone
from tpm.models import Department
from delays.models import DelayRecord, DelayUpload

def parse_date_string(date_str):
    """
    Tries to parse a date string using various formats.
    Returns a datetime.date object if successful, else None.
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Strip prefixes like "DATE :", "DATE:", etc.
    date_str = re.sub(r'(?i)^date\s*:\s*[-]*\s*>', '', date_str).strip()
    date_str = re.sub(r'(?i)^date\s*:\s*', '', date_str).strip()
    
    # Try different formats
    formats = [
        '%d.%m.%Y', '%d.%m.%y',
        '%d-%m-%Y', '%d-%m-%y',
        '%Y-%m-%d',
        '%d-%b-%Y', '%d-%b-%y', # e.g. 10-Jun-2026
        '%d %b %Y', '%d %b %y',
        '%d %B %Y', '%d %B %y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    # Try searching for a date pattern inside the string
    match = re.search(r'\d{2}[.-]\d{2}[.-]\d{4}', date_str)
    if match:
        for fmt in ['%d.%m.%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(match.group(0), fmt).date()
            except ValueError:
                continue
                
    match_alpha = re.search(r'\d{1,2}[- ][A-Za-z]{3}[- ]\d{4}', date_str)
    if match_alpha:
        for fmt in ['%d-%b-%Y', '%d %b %Y']:
            try:
                return datetime.strptime(match_alpha.group(0), fmt).date()
            except ValueError:
                continue

    return None


def sheet_to_rows(sheet, is_xlsx=True):
    """
    Unified utility to extract all sheet cells as a list of lists of values.
    """
    if is_xlsx:
        # For openpyxl
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    else:
        # For xlrd
        rows = []
        for r in range(sheet.nrows):
            row_vals = []
            for c in range(sheet.ncols):
                val = sheet.cell_value(r, c)
                # xlrd floats dates sometimes, convert if date type
                ctype = sheet.cell_type(r, c)
                if ctype == xlrd.XL_CELL_DATE:
                    try:
                        date_tuple = xlrd.xldate_as_tuple(val, sheet.book.datemode)
                        val = datetime(*date_tuple)
                    except Exception:
                        pass
                row_vals.append(val)
            rows.append(row_vals)
        return rows


def parse_sms3_sheet(rows, sheet_name, department, upload):
    """
    Parses a single SMS-III day delay sheet.
    """
    # Find the Date (usually row 1, col 0 contains 'DATE : 30.05.2026')
    sheet_date = None
    for r in range(min(len(rows), 5)):
        row = rows[r]
        if row and len(row) > 0 and row[0]:
            val = str(row[0])
            if 'DATE' in val.upper():
                sheet_date = parse_date_string(val)
                break
                
    if not sheet_date:
        # Try to parse date from sheet name (e.g. "30" of May 2026)
        # Fallback to current date month/year if sheet is named like "30"
        try:
            day = int(sheet_name.strip())
            now = timezone.now()
            # Default to May 2026 since files are for May 2026
            sheet_date = date(2026, 5, day)
        except Exception:
            sheet_date = timezone.now().date()

    # Find the starts of the delays section
    # Usually Row 9: ['DELAYS', 'AGENCY', '', '', '', '', 'TOTAL(Min.)', 'HRS']
    start_row = 10
    found_header = False
    for r in range(min(len(rows), 15)):
        row = rows[r]
        if row and len(row) > 1 and row[0] and row[1]:
            if 'DELAYS' in str(row[0]).upper() and 'AGENCY' in str(row[1]).upper():
                start_row = r + 1
                found_header = True
                break

    records_created = 0
    # Process rows
    for r in range(start_row, len(rows)):
        row = rows[r]
        if not row or len(row) < 7:
            continue
            
        desc = row[0]
        agency = row[1]
        
        # Stop check
        if desc and ('TOTAL' in str(desc).upper() or 'SUM' in str(desc).upper()):
            break
            
        # Get total mins (Col index 6)
        total_mins_val = row[6]
        
        # Skip empty or spacer rows
        if not desc and not agency and (total_mins_val == '' or total_mins_val is None or total_mins_val == 0.0):
            continue
            
        # Parse duration
        try:
            duration = float(total_mins_val) if total_mins_val not in (None, '', '-') else 0.0
        except ValueError:
            duration = 0.0
            
        if duration <= 0.0 and (not desc or desc == '-'):
            continue
            
        # Extrapolate shifts
        shift_c = row[3] if len(row) > 3 else ''
        shift_a = row[4] if len(row) > 4 else ''
        shift_b = row[5] if len(row) > 5 else ''
        
        time_slots = []
        if shift_c and shift_c not in ('', '-'): time_slots.append(f"Shift C ({shift_c}m)")
        if shift_a and shift_a not in ('', '-'): time_slots.append(f"Shift A ({shift_a}m)")
        if shift_b and shift_b not in ('', '-'): time_slots.append(f"Shift B ({shift_b}m)")
        time_slot = ", ".join(time_slots) if time_slots else "Daily Log"
        
        # Save record
        DelayRecord.objects.create(
            upload=upload,
            department=department,
            sheet_name=sheet_name,
            date=sheet_date,
            time_slot=time_slot,
            duration_mins=duration,
            agency=str(agency).strip() if agency else 'Unknown Agency',
            description=str(desc).strip() if desc else 'No Description',
        )
        records_created += 1
        
    return records_created


def parse_rail_mill_sheet(rows, sheet_name, department, upload):
    """
    Parses the Rail Mill Delay_Report sheet.
    """
    # Find sheet date
    # Row 2 (index 2) has 'RAIL MILL DELAY REPORT FOR 09-06-2026'
    # Row 3 (index 3) has C4 '10-Jun-2026'
    sheet_date = None
    for r in range(min(len(rows), 8)):
        row = rows[r]
        for val in row:
            if val and ('REPORT FOR' in str(val).upper() or 'DATE' in str(val).upper()):
                sheet_date = parse_date_string(val)
                if sheet_date:
                    break
        if sheet_date:
            break
            
    if not sheet_date:
        sheet_date = timezone.now().date()

    # Find the header row index
    header_row_idx = 7
    for r in range(min(len(rows), 15)):
        row = rows[r]
        if row and len(row) > 7 and 'Hrs(Time)' in [str(x) for x in row]:
            header_row_idx = r
            break

    records_created = 0
    propagated_date = sheet_date
    propagated_time_slot = ""

    # Process rows below header
    for r in range(header_row_idx + 1, len(rows)):
        row = rows[r]
        if not row or len(row) < 17:
            continue
            
        time_val = row[0]
        # Check stop condition
        if time_val and ('TOTAL' in str(time_val).upper() or 'SUM' in str(time_val).upper()):
            break
            
        duration_val = row[6]
        
        # If duration is '-' or empty, skip
        if duration_val in (None, '', '-'):
            continue
            
        try:
            duration = float(duration_val)
        except ValueError:
            continue
            
        if duration <= 0.0:
            continue
            
        # Parse date and time from time_val if available
        # e.g., '08-06-2026 22:00 - 23:00'
        row_date = propagated_date
        time_slot = propagated_time_slot
        
        if time_val:
            time_val_str = str(time_val).strip()
            # Try to extract date
            date_match = re.search(r'\d{2}[.-]\d{2}[.-]\d{4}', time_val_str)
            if date_match:
                parsed_row_date = parse_date_string(date_match.group(0))
                if parsed_row_date:
                    row_date = parsed_row_date
                    propagated_date = parsed_row_date
            
            # Try to extract time slot (e.g., '22:00 - 23:00')
            time_match = re.search(r'\d{2}:\d{2}\s*-\s*\d{2}:\d{2}', time_val_str)
            if time_match:
                time_slot = time_match.group(0)
                propagated_time_slot = time_slot
            else:
                # Fallback to the rest of the text
                time_slot = time_val_str
                propagated_time_slot = time_slot
                
        # Agency (Col index 9)
        agency = row[9] if row[9] and row[9] != '-' else 'Unknown Agency'
        sub_agency = row[10] if row[10] and row[10] != '-' else ''
        section = row[11] if row[11] and row[11] != '-' else ''
        equipment = row[13] if row[13] and row[13] != '-' else ''
        sub_equipment = row[14] if row[14] and row[14] != '-' else ''
        shift_incharge = row[15] if row[15] and row[15] != '-' else ''
        description = row[16] if row[16] and row[16] != '-' else 'No Description'
        why = row[17] if len(row) > 17 and row[17] and row[17] != '-' else ''
        
        # Save record
        DelayRecord.objects.create(
            upload=upload,
            department=department,
            sheet_name=sheet_name,
            date=row_date,
            time_slot=time_slot,
            start_time=row[4] if row[4] != '-' else None,
            end_time=row[5] if row[5] != '-' else None,
            duration_mins=duration,
            agency=str(agency).strip(),
            sub_agency=str(sub_agency).strip() if sub_agency else None,
            section=str(section).strip() if section else None,
            equipment=str(equipment).strip() if equipment else None,
            sub_equipment=str(sub_equipment).strip() if sub_equipment else None,
            shift_incharge=str(shift_incharge).strip() if shift_incharge else None,
            description=str(description).strip(),
            why=str(why).strip() if why else None,
        )
        records_created += 1

    return records_created


def parse_generic_sheet(rows, sheet_name, department, upload):
    """
    Heuristic fallback parser to handle arbitrary delay sheets.
    """
    # 1. Scan rows to find a header row
    header_row_idx = None
    col_mapping = {}
    
    keywords = {
        'date': ['date', 'day'],
        'time': ['time', 'slot', 'hour', 'hrs', 'from', 'to'],
        'duration': ['min', 'minutes', 'duration', 'downtime', 'hours', 'hrs'],
        'agency': ['agency', 'dept', 'responsibility', 'department'],
        'description': ['reason', 'cause', 'description', 'detail', 'problem', 'delays'],
        'equipment': ['equipment', 'asset', 'machine', 'sub equipment'],
        'incharge': ['incharge', 'staff', 'user', 'operator', 'shift']
    }
    
    for r in range(min(len(rows), 20)):
        row = rows[r]
        if not row:
            continue
            
        matches = 0
        temp_mapping = {}
        for c, val in enumerate(row):
            if not val:
                continue
            val_str = str(val).lower().strip()
            
            for key, kw_list in keywords.items():
                if any(kw in val_str for kw in kw_list):
                    # We pick the first matching key or prioritize
                    if key not in temp_mapping:
                        temp_mapping[key] = c
                        matches += 1
                        
        if matches >= 3:
            # We found a header row!
            header_row_idx = r
            col_mapping = temp_mapping
            break
            
    if header_row_idx is None:
        # Let's see if we can do a default mapping (0: desc, 1: agency, 2: duration)
        # If there are columns, just do a basic fallback
        return 0

    # Find sheet-level date as backup
    sheet_date = None
    for r in range(min(len(rows), header_row_idx + 1)):
        for val in rows[r]:
            if val:
                sheet_date = parse_date_string(val)
                if sheet_date:
                    break
        if sheet_date:
            break
            
    if not sheet_date:
        sheet_date = timezone.now().date()

    records_created = 0
    # Parse rows below headers
    for r in range(header_row_idx + 1, len(rows)):
        row = rows[r]
        if not row:
            continue
            
        # Stop condition: check if first cells are totals
        first_val = str(row[0]).upper() if row[0] else ''
        if 'TOTAL' in first_val or 'SUM' in first_val:
            break
            
        # Extract columns
        desc_idx = col_mapping.get('description', 0)
        agency_idx = col_mapping.get('agency', 1)
        dur_idx = col_mapping.get('duration', None)
        
        if dur_idx is None:
            # Skip if we can't find duration column
            continue
            
        desc = row[desc_idx] if desc_idx < len(row) else None
        agency = row[agency_idx] if agency_idx < len(row) else 'General'
        duration_val = row[dur_idx] if dur_idx < len(row) else 0.0
        
        if not desc and (duration_val is None or duration_val == '' or duration_val == 0.0):
            continue
            
        try:
            duration = float(duration_val) if duration_val not in (None, '', '-') else 0.0
        except ValueError:
            duration = 0.0
            
        if duration <= 0.0 and (not desc or desc == '-'):
            continue
            
        # Date parsing
        row_date = sheet_date
        date_idx = col_mapping.get('date', None)
        if date_idx is not None and date_idx < len(row) and row[date_idx]:
            parsed = parse_date_string(row[date_idx])
            if parsed:
                row_date = parsed
                
        # Other optional fields
        time_slot = ""
        time_idx = col_mapping.get('time', None)
        if time_idx is not None and time_idx < len(row) and row[time_idx]:
            time_slot = str(row[time_idx])
            
        equipment = ""
        equip_idx = col_mapping.get('equipment', None)
        if equip_idx is not None and equip_idx < len(row) and row[equip_idx]:
            equipment = str(row[equip_idx])
            
        incharge = ""
        incharge_idx = col_mapping.get('incharge', None)
        if incharge_idx is not None and incharge_idx < len(row) and row[incharge_idx]:
            incharge = str(row[incharge_idx])
            
        # Save record
        DelayRecord.objects.create(
            upload=upload,
            department=department,
            sheet_name=sheet_name,
            date=row_date,
            time_slot=time_slot,
            duration_mins=duration,
            agency=str(agency).strip() if agency else 'General',
            equipment=str(equipment).strip() if equipment else None,
            shift_incharge=str(incharge).strip() if incharge else None,
            description=str(desc).strip() if desc else 'No Description',
        )
        records_created += 1
        
    return records_created


def parse_excel_file(upload_instance):
    """
    Main parser entrypoint.
    Opens the excel file, detects sheet layouts, extracts delay logs,
    and updates the upload_instance status.
    """
    file_path = upload_instance.file.path
    department = upload_instance.department
    
    if not os.path.exists(file_path):
        upload_instance.status = 'FAILED'
        upload_instance.error_message = f"File not found at path: {file_path}"
        upload_instance.save()
        return False
        
    _, ext = os.path.splitext(file_path.lower())
    is_xlsx = ext == '.xlsx'
    
    total_records = 0
    
    try:
        with transaction.atomic():
            # Open the workbook
            if is_xlsx:
                wb = openpyxl.load_workbook(file_path, data_only=True)
                sheet_names = wb.sheetnames
            else:
                wb = xlrd.open_workbook(file_path)
                sheet_names = wb.sheet_names()
                
            # Loop through worksheets
            for sh_name in sheet_names:
                if is_xlsx:
                    sheet = wb[sh_name]
                else:
                    sheet = wb.sheet_by_name(sh_name)
                    
                rows = sheet_to_rows(sheet, is_xlsx=is_xlsx)
                if not rows:
                    continue
                    
                # ─────────────────────────────────────────────────────────────
                # DETECT LAYOUT FORMAT
                # ─────────────────────────────────────────────────────────────
                is_sms3 = False
                is_rail_mill = False
                
                # Check SMS3 criteria: DELAYS header in col A, AGENCY in col B (usually row 9 or index 9)
                for r in range(min(len(rows), 15)):
                    row = rows[r]
                    if row and len(row) > 1 and row[0] and row[1]:
                        if 'DELAYS' in str(row[0]).upper() and 'AGENCY' in str(row[1]).upper():
                            is_sms3 = True
                            break
                            
                # Check Rail Mill criteria: Hrs(Time) header in col 0, Description for delay in col 16 (index 16)
                for r in range(min(len(rows), 15)):
                    row = rows[r]
                    if row and len(row) > 16:
                        # Col 0: Hrs(Time), Col 16: Description for delay
                        row_strs = [str(x).upper() for x in row if x is not None]
                        if any('HRS(TIME)' in s for s in row_strs) and any('DESCRIPTION FOR DELAY' in s or 'DESCRIPTION' in s for s in row_strs):
                            is_rail_mill = True
                            break
                            
                # Parse depending on type
                if is_sms3:
                    count = parse_sms3_sheet(rows, sh_name, department, upload_instance)
                    total_records += count
                elif is_rail_mill:
                    if 'SUMMARY' not in sh_name.upper(): # Skip summary sheet
                        count = parse_rail_mill_sheet(rows, sh_name, department, upload_instance)
                        total_records += count
                else:
                    # Generic fallback parser
                    # Skip typical summary sheet names
                    if 'SUMMARY' not in sh_name.upper() and 'KPI' not in sh_name.upper() and 'LOSS' not in sh_name.upper():
                        count = parse_generic_sheet(rows, sh_name, department, upload_instance)
                        total_records += count
                        
            # Update upload status
            upload_instance.status = 'SUCCESS'
            upload_instance.error_message = f"Successfully parsed {total_records} delay records."
            upload_instance.save()
            return True
            
    except Exception as e:
        upload_instance.status = 'FAILED'
        upload_instance.error_message = f"Error during parsing: {str(e)}"
        upload_instance.save()
        raise e
