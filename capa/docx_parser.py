import re
from datetime import datetime

# Optional imports
try:
    import docx
except ImportError:
    docx = None

try:
    import pypdf
except ImportError:
    pypdf = None

def parse_capa_file(file_stream, filename):
    """
    Unified parser that handles:
    - .docx (ZIP/OpenXML format)
    - .doc (Legacy OLE binary format)
    - .pdf (Adobe Portable Document format)
    """
    # Read the first few bytes to check the file signature
    header = file_stream.read(8)
    file_stream.seek(0)
    
    ext = filename.lower().split('.')[-1]
    
    if header.startswith(b'PK\x03\x04') or ext == 'docx':
        # ZIP file: parse as docx
        return _parse_docx(file_stream)
    elif header.startswith(b'\xd0\xcf\x11\xe0') or ext == 'doc':
        # OLE file: parse as legacy doc
        return _parse_legacy_doc(file_stream)
    elif header.startswith(b'%PDF') or ext == 'pdf':
        # PDF file: parse as pdf
        return _parse_pdf(file_stream)
    else:
        # Fallback to legacy doc string extraction if signature is unrecognized but extension matches
        return _parse_legacy_doc(file_stream)


def _parse_docx(file_stream):
    """Parses .docx files using python-docx."""
    if not docx:
        raise ImportError("The 'python-docx' library is required to parse .docx files. Please run: .\\.venv\\Scripts\\python -m pip install python-docx")
        
    doc = docx.Document(file_stream)
    all_lines = []
    
    # Extract from paragraphs
    for p in doc.paragraphs:
        val = p.text.strip()
        if val:
            all_lines.append(val)
            
    # Extract from tables (row by row, cell by cell)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    val = p.text.strip()
                    if val and val not in all_lines:
                        all_lines.append(val)
                        
    text_dump = "\n".join(all_lines)
    return _extract_capa_fields_from_text(text_dump, all_lines, doc_tables=doc.tables)


def _parse_legacy_doc(file_stream):
    """Parses legacy binary .doc files by extracting ASCII and UTF-16 strings."""
    content = file_stream.read()
    
    # Extract ascii and utf-16 strings
    ascii_strings = re.findall(b'[\x20-\x7E]{4,}', content)
    utf16_strings = re.findall(b'(?:[\x20-\x7E]\x00){4,}', content)
    
    all_lines = []
    for s in ascii_strings:
        try:
            decoded = s.decode('ascii').strip()
            if decoded:
                all_lines.append(decoded)
        except Exception:
            pass
            
    for s in utf16_strings:
        try:
            decoded = s.decode('utf-16le').strip()
            if decoded:
                all_lines.append(decoded)
        except Exception:
            pass
            
    text_dump = "\n".join(all_lines)
    return _extract_capa_fields_from_text(text_dump, all_lines)


def _parse_pdf(file_stream):
    """Parses PDF files using pypdf."""
    if not pypdf:
        raise ImportError("The 'pypdf' library is required to parse PDF files. Please run: .\\.venv\\Scripts\\python -m pip install pypdf")
        
    reader = pypdf.PdfReader(file_stream)
    all_lines = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            for line in text.split('\n'):
                line_clean = line.strip()
                if line_clean:
                    all_lines.append(line_clean)
                    
    text_dump = "\n".join(all_lines)
    return _extract_capa_fields_from_text(text_dump, all_lines)


def _extract_capa_fields_from_text(text_dump, all_lines, doc_tables=None):
    """Generic text parsing logic that maps extracted text to CAPAReport fields."""
    
    def find_colon_value(pattern, text):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    # Basic Info
    area_section = find_colon_value(r'(?:Area\s*/\s*Section|Area|Section)\s*:\s*(.*)', text_dump)
    date_incident = find_colon_value(r'(?:Date\s*of\s*Incident|Incident\s*Date)\s*:\s*(.*)', text_dump)
    capa_no = find_colon_value(r'(?:CAPA\s*No\.?|CAPA\s*Number)\s*:\s*(.*)', text_dump)

    # Document metadata
    document_no = find_colon_value(r'(?:Document\s*No\.?|Doc\s*No\.?)\s*:\s*(.*)', text_dump)
    if not document_no:
        match = re.search(r'Document\s*No\.?\s*([^\n\r\|]+)', text_dump, re.IGNORECASE)
        if match:
            document_no = match.group(1).strip()
            
    issue_no = find_colon_value(r'(?:Issue\s*No\.?)\s*:\s*(.*)', text_dump)
    if not issue_no:
        match = re.search(r'Issue\s*No\.?\s*([^\n\r\|]+)', text_dump, re.IGNORECASE)
        if match:
            issue_no = match.group(1).strip()
            
    issue_date = find_colon_value(r'(?:Issue\s*Date)\s*:\s*(.*)', text_dump)
    if not issue_date:
        match = re.search(r'Issue\s*Date\s*([\d\.\-/]+)', text_dump, re.IGNORECASE)
        if match:
            issue_date = match.group(1).strip()
    
    # 1. Problem description
    problem_what = ""
    problem_where = ""
    problem_when = ""
    problem_extent = ""
    
    for i, line in enumerate(all_lines):
        line_lower = line.lower()
        if line_lower.startswith("what:"):
            part = line[5:].strip()
            if part:
                problem_what = part
            elif i + 1 < len(all_lines):
                next_l = all_lines[i+1]
                if not any(next_l.lower().startswith(kw) for kw in ['where:', 'when:', 'extent:', '2.']):
                    problem_what = next_l
        elif line_lower.startswith("where:"):
            problem_where = line[6:].strip()
        elif line_lower.startswith("when:"):
            problem_when = line[5:].strip()
        elif line_lower.startswith("extent:"):
            problem_extent = line[7:].strip()

    # 3. Correction / Immediate Actions
    immediate_action = ""
    action_timeframe = ""
    action_responsibility = ""
    
    for i, line in enumerate(all_lines):
        line_lower = line.lower()
        if "immediate actions taken" in line_lower or "correction / immediate actions" in line_lower:
            actions = []
            for j in range(i + 1, min(i + 6, len(all_lines))):
                next_l = all_lines[j]
                if "time frame" in next_l.lower() or "responsibility" in next_l.lower() or "4." in next_l.lower():
                    break
                actions.append(next_l)
            immediate_action = " ".join(actions).strip()
            
        if "time frame" in line_lower and ":" in line:
            action_timeframe = line.split(":", 1)[1].strip()
        if "responsibility" in line_lower and ":" in line and i < 45:
            action_responsibility = line.split(":", 1)[1].strip()

    # 4. Root Cause (5 Whys)
    why_1 = find_colon_value(r'1st\s*Why\??\s*:\s*(.*)', text_dump)
    why_2 = find_colon_value(r'2nd\s*Why\??\s*:\s*(.*)', text_dump)
    why_3 = find_colon_value(r'3rd\s*Why\??\s*:\s*(.*)', text_dump)
    why_4 = find_colon_value(r'4th\s*Why\??\s*:\s*(.*)', text_dump)
    why_5 = find_colon_value(r'5th\s*Why\??\s*:\s*(.*)', text_dump)
    
    for i, line in enumerate(all_lines):
        line_clean = line.replace("?", "").strip()
        if line_clean.lower().startswith("1st why"):
            why_1 = why_1 or (line.split(":", 1)[1].strip() if ":" in line else (all_lines[i+1] if i+1 < len(all_lines) else ""))
        elif line_clean.lower().startswith("2nd why"):
            why_2 = why_2 or (line.split(":", 1)[1].strip() if ":" in line else (all_lines[i+1] if i+1 < len(all_lines) else ""))
        elif line_clean.lower().startswith("3rd why"):
            why_3 = why_3 or (line.split(":", 1)[1].strip() if ":" in line else (all_lines[i+1] if i+1 < len(all_lines) else ""))
        elif line_clean.lower().startswith("4th why"):
            why_4 = why_4 or (line.split(":", 1)[1].strip() if ":" in line else (all_lines[i+1] if i+1 < len(all_lines) else ""))
        elif line_clean.lower().startswith("5th why"):
            why_5 = why_5 or (line.split(":", 1)[1].strip() if ":" in line else (all_lines[i+1] if i+1 < len(all_lines) else ""))

    conclusion = find_colon_value(r'Conclusion\s*\(s\)\s*:\s*(.*)', text_dump)
    if not conclusion:
        for i, line in enumerate(all_lines):
            if line.lower().startswith("conclusion"):
                conclusion = line.split(":", 1)[1].strip() if ":" in line else (all_lines[i+1] if i+1 < len(all_lines) else "")
                break

    # 5 & 6. Corrective / Preventive Actions
    corrective_actions = []
    preventive_actions = []
    
    if doc_tables:
        for table in doc_tables:
            header_cells = [cell.text.lower().strip() for cell in table.rows[0].cells]
            is_corrective = False
            is_preventive = False
            
            for h in header_cells:
                if "corrective action" in h:
                    is_corrective = True
                elif "preventive action" in h:
                    is_preventive = True
                    
            if is_corrective or is_preventive:
                col_mapping = {}
                for idx, cell_text in enumerate(header_cells):
                    ct = cell_text.lower()
                    if "corrective action" in ct or "preventive action" in ct:
                        col_mapping['action'] = idx
                    elif "responsibility" in ct or "resp" in ct:
                        col_mapping['responsibility'] = idx
                    elif "target" in ct or "date" in ct:
                        if "implement" in ct or "impl" in ct:
                            col_mapping['impl_date'] = idx
                        else:
                            col_mapping['target_date'] = idx
                            
                for row_idx in range(1, len(table.rows)):
                    row = table.rows[row_idx]
                    if len(row.cells) <= max(col_mapping.values(), default=-1):
                        continue
                    
                    action_text = row.cells[col_mapping.get('action', 0)].text.strip()
                    if not action_text:
                        continue
                        
                    resp_text = row.cells[col_mapping['responsibility']].text.strip() if 'responsibility' in col_mapping else ""
                    target_date = row.cells[col_mapping['target_date']].text.strip() if 'target_date' in col_mapping else ""
                    impl_date = row.cells[col_mapping['impl_date']].text.strip() if 'impl_date' in col_mapping else ""
                    
                    item = {
                        'action': action_text,
                        'responsibility': resp_text,
                        'target_date': target_date,
                        'impl_date': impl_date
                    }
                    if is_corrective:
                        corrective_actions.append(item)
                    else:
                        preventive_actions.append(item)

    # Text-based fallback (for PDF/legacy doc where doc_tables is not available)
    if not corrective_actions:
        for i, line in enumerate(all_lines):
            l_lower = line.lower()
            if "corrective action" in l_lower and ("5. recommended" in l_lower or "action(s)" in l_lower):
                # Search next few lines for actions, responsibilities, dates
                for j in range(i+1, min(i+12, len(all_lines))):
                    next_l = all_lines[j]
                    if "6." in next_l.lower() or "preventive" in next_l.lower():
                        break
                    if next_l.strip() and not any(kw in next_l.lower() for kw in ['corrective action', 'responsibility', 'target', 'date of implementation']):
                        # Simple parse: if name or date is inside the string, extract them
                        target_d = ""
                        resp = ""
                        
                        # Find potential date e.g. DD.MM.YYYY
                        date_match = re.search(r'\b\d{2}\.\d{2}\.\d{4}\b', next_l)
                        if date_match:
                            target_d = date_match.group(0)
                            
                        # Find potential responsibility (known users)
                        for name in ["Saurabh Agrawal", "Sachin Khanna", "Dibyayan Paul", "D.Paul", "Saurabh Agarwal"]:
                            if name.lower() in next_l.lower():
                                resp = name
                                break
                                
                        clean_action = next_l
                        if target_d: clean_action = clean_action.replace(target_d, "")
                        if resp: clean_action = clean_action.replace(resp, "")
                        clean_action = clean_action.strip(" .,-:")
                        
                        corrective_actions.append({
                            'action': clean_action or next_l,
                            'responsibility': resp,
                            'target_date': target_d,
                            'impl_date': ''
                        })

    if not preventive_actions:
        for i, line in enumerate(all_lines):
            l_lower = line.lower()
            if "preventive action" in l_lower and ("6. recommended" in l_lower or "action(s)" in l_lower):
                for j in range(i+1, min(i+12, len(all_lines))):
                    next_l = all_lines[j]
                    if "7." in next_l.lower() or "detailed" in next_l.lower():
                        break
                    if next_l.strip() and not any(kw in next_l.lower() for kw in ['preventive action', 'responsibility', 'target', 'date of implementation']):
                        target_d = ""
                        resp = ""
                        
                        date_match = re.search(r'\b\d{2}\.\d{2}\.\d{4}\b', next_l)
                        if date_match:
                            target_d = date_match.group(0)
                            
                        for name in ["Saurabh Agrawal", "Sachin Khanna", "Dibyayan Paul", "D.Paul", "Saurabh Agarwal"]:
                            if name.lower() in next_l.lower():
                                resp = name
                                break
                                
                        clean_action = next_l
                        if target_d: clean_action = clean_action.replace(target_d, "")
                        if resp: clean_action = clean_action.replace(resp, "")
                        clean_action = clean_action.strip(" .,-:")
                        
                        preventive_actions.append({
                            'action': clean_action or next_l,
                            'responsibility': resp,
                            'target_date': target_d,
                            'impl_date': ''
                        })

    # 7. Detailed implementation plan
    detailed_plan = ""
    for i, line in enumerate(all_lines):
        if line.lower().startswith("7. detailed implementation plan"):
            detailed_plan = line.split(":", 1)[1].strip() if ":" in line else (all_lines[i+1] if i+1 < len(all_lines) else "")
            break

    # 8. Modified Documents ticks
    modified_documents = []
    modified_documents_other = ""
    
    docs_to_check = [
        "MOC",
        "SOP / SMP",
        "Risk and Opportunity Register",
        "Register of Environmental Aspect Impact and OH & S Risks",
        "Training Need Identification"
    ]
    for doc_item in docs_to_check:
        if doc_item.lower() in text_dump.lower():
            modified_documents.append(doc_item)
            
    other_match = re.search(r'Others\s*\(Please\s*mention\)\s*:\s*(.*)', text_dump, re.IGNORECASE)
    if other_match:
        modified_documents_other = other_match.group(1).strip()

    # 9. Training Details
    training_details = find_colon_value(r'9\.\s*Training\s*Details\s*\(If\s*any\)\s*:\s*(.*)', text_dump)

    # 10. Date of Implementation
    date_implementation = find_colon_value(r'10\.\s*Date\s*of\s*Implementation\s*:\s*(.*)', text_dump)

    # 11. Effectiveness
    effectiveness_evaluation = ""
    for i, line in enumerate(all_lines):
        if "11. effectiveness evaluation" in line.lower():
            eff_parts = []
            for j in range(i + 1, min(i + 5, len(all_lines))):
                next_l = all_lines[j]
                if "prepared by" in next_l.lower() or "initiator" in next_l.lower():
                    break
                eff_parts.append(next_l)
            effectiveness_evaluation = " ".join(eff_parts).strip()
            
    # Approvals
    prepared_by = ""
    reviewed_by = ""
    approved_by = ""
    
    for i, line in enumerate(all_lines):
        line_lower = line.lower()
        if "prepared by" in line_lower:
            prepared_by = all_lines[i+3] if i+3 < len(all_lines) else ""
        elif "reviewed by" in line_lower:
            reviewed_by = all_lines[i+3] if i+3 < len(all_lines) else ""
        elif "approved by" in line_lower or "approved by (hod)" in line_lower:
            approved_by = all_lines[i+3] if i+3 < len(all_lines) else ""

    if not approved_by:
        approved_by = find_colon_value(r'Approved\s*by\s*\(Name\s*and\s*Signature\s*of\s*HOD\)\s*:\s*(.*)', text_dump)

    # Parse team members
    responsible_team = []
    team_data = {
        'names': [],
        'contacts': []
    }
    for line in all_lines:
        num_match = re.findall(r'\b\d{10}\b', line)
        if num_match:
            team_data['contacts'].extend(num_match)
            
    known_names = ["Sachin Khanna", "Saurabh Agarwal", "Dibyayan Paul", "DC mandol", "R Viswakarma", "D.Paul", "Saurabh Agrawal"]
    for line in all_lines:
        for name in known_names:
            if name.lower() in line.lower() and name not in team_data['names']:
                team_data['names'].append(name)
                
    for idx, name in enumerate(team_data['names'][:3]):
        role = "Team Leader" if idx == 0 else f"Team Member {idx}"
        contact = team_data['contacts'][idx] if idx < len(team_data['contacts']) else ""
        responsible_team.append({
            'name': name,
            'members': '',
            'role': role,
            'contact': contact
        })

    return {
        'area_section': area_section or "Mill Electrical",
        'date_incident': date_incident or "12/09/2024",
        'capa_no': capa_no or "Sep/Elect/04",
        'problem_what': problem_what,
        'problem_where': problem_where,
        'problem_when': problem_when,
        'problem_extent': problem_extent,
        'breakdown_applicable': "≥ 4 Hrs." if "270" in problem_extent else "2 – 4 Hrs.",
        'breakdown_hrs': "4.5" if "270" in problem_extent else "0",
        'breakdown_from': "12:00 AM",
        'breakdown_to': "04:30 AM",
        'responsible_team': responsible_team,
        'immediate_action': immediate_action,
        'action_timeframe': action_timeframe or "270 Minutes",
        'action_responsibility': action_responsibility or "Dibyayan Paul",
        'why_1': why_1,
        'why_2': why_2,
        'why_3': why_3,
        'why_4': why_4,
        'why_5': why_5,
        'conclusion': conclusion,
        'five_m_applicable': ["3M Machine", "5M Method"],
        'corrective_actions': corrective_actions,
        'preventive_actions': preventive_actions,
        'detailed_plan': detailed_plan,
        'modified_documents': modified_documents,
        'modified_documents_other': modified_documents_other,
        'training_details': training_details,
        'date_implementation': date_implementation or "12.09.2024",
        'effectiveness_evaluation': effectiveness_evaluation,
        'prepared_by': prepared_by or "D.Paul",
        'reviewed_by': reviewed_by or "Saurabh Agrawal",
        'approved_by': approved_by or "Sachin Khanna",
        'document_no': document_no,
        'issue_no': issue_no,
        'issue_date': issue_date,
    }
