import json
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Count, Q
from django.urls import reverse

from tpm.models import Department, User, CAPAReport, CAPADocxUpload
from portal.utils.decorators import dept_visibility_required, module_access_required
from .docx_parser import parse_capa_file

# For PDF export
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

@login_required
@dept_visibility_required
@module_access_required('CAPA')
def capa_dashboard(request, dept_id):
    active_dept = get_object_or_404(Department, id=dept_id)
    
    # Retrieve all uploads & reports for this department
    uploads = CAPADocxUpload.objects.filter(department=active_dept).order_by('-uploaded_at')
    reports = CAPAReport.objects.filter(department=active_dept)
    
    total_capas = reports.count()
    open_capas = reports.filter(status__in=['Open', 'In Progress']).count()
    closed_capas = reports.filter(status='Closed').count()
    
    # Comparative sheets table data
    sheet_comparisons = []
    
    # 1. Check Docx Uploads
    for u in uploads:
        recs = u.reports.all()
        if recs.exists():
            sheet_comparisons.append({
                'id': u.id,
                'name': u.filename,
                'date': u.upload_date.strftime('%d.%m.%Y') if u.upload_date else '—',
                'total': recs.count(),
                'open': recs.filter(status__in=['Open', 'In Progress']).count(),
                'closed': recs.filter(status='Closed').count(),
            })
            
    # 2. Check default manual list
    manual_recs = reports.filter(docx_upload=None)
    if manual_recs.exists():
        sheet_comparisons.append({
            'id': 'new_file',
            'name': 'Default manual list',
            'date': '—',
            'total': manual_recs.count(),
            'open': manual_recs.filter(status__in=['Open', 'In Progress']).count(),
            'closed': manual_recs.filter(status='Closed').count(),
        })
        
    comp_labels = [item['name'] for item in sheet_comparisons]
    comp_ids = [item['id'] for item in sheet_comparisons]
    comp_total = [item['total'] for item in sheet_comparisons]
    comp_open = [item['open'] for item in sheet_comparisons]
    comp_closed = [item['closed'] for item in sheet_comparisons]
    
    # Donut Chart Data
    status_chart_data = [closed_capas, open_capas] # Closed vs Open/In-Progress
    
    context = {
        'active_dept_id': dept_id,
        'active_dept': active_dept,
        'active_module': 'CAPA',
        'active_tab': 'dashboard',
        
        # Metrics
        'total_capas': total_capas,
        'open_capas': open_capas,
        'closed_capas': closed_capas,
        
        # Table lists
        'sheet_comparisons': sheet_comparisons,
        
        # Chart JSON lists
        'comp_labels': json.dumps(comp_labels),
        'comp_ids': json.dumps(comp_ids),
        'comp_total': json.dumps(comp_total),
        'comp_open': json.dumps(comp_open),
        'comp_closed': json.dumps(comp_closed),
        'status_chart_data': json.dumps(status_chart_data),
    }
    return render(request, 'capa/dashboard.html', context)

@login_required
@dept_visibility_required
@module_access_required('CAPA')
def capa_identification(request, dept_id):
    active_dept = get_object_or_404(Department, id=dept_id)
    owners = User.objects.filter(is_active=True).order_by('first_name')
    uploads = CAPADocxUpload.objects.filter(department=active_dept).order_by('-uploaded_at')
    
    import random
    # Pre-fills for team, corrective and preventive actions
    prefills = {
        'capa_no': f"CAPA-{active_dept.code}-{(CAPAReport.objects.filter(department=active_dept).count() + 1):03d}",
        'document_no': f"{datetime.now().year}/DOC-{random.randint(100, 999)}/{active_dept.code}",
        'issue_no': str(random.randint(1, 12)),
        'issue_date': datetime.now().strftime('%d.%m.%Y'),
        'responsible_team': [
            {'name': '', 'members': '', 'role': 'Team Leader', 'contact': ''},
            {'name': '', 'members': '', 'role': 'Team Member 1', 'contact': ''},
            {'name': '', 'members': '', 'role': 'Team Member 2', 'contact': ''},
        ],
        'corrective_actions': [
            {'action': '', 'responsibility': '', 'target_date': '', 'impl_date': ''},
        ],
        'preventive_actions': [
            {'action': '', 'responsibility': '', 'target_date': '', 'impl_date': ''},
        ]
    }
    
    context = {
        'active_dept_id': dept_id,
        'active_dept': active_dept,
        'active_module': 'CAPA',
        'active_tab': 'identification',
        'owners': owners,
        'today': datetime.now().strftime('%Y-%m-%d'),
        'uploads': uploads,
        'prefills': prefills,
    }
    return render(request, 'capa/manual_entry.html', context)

@login_required
@dept_visibility_required
@module_access_required('CAPA')
def capa_report(request, dept_id):
    active_dept = get_object_or_404(Department, id=dept_id)
    uploads = CAPADocxUpload.objects.filter(department=active_dept).order_by('-uploaded_at')
    
    upload_id = request.GET.get('upload_id')
    selected_upload_id = 'new_file'
    selected_upload = None
    
    if upload_id and upload_id != 'new_file':
        try:
            selected_upload_id = int(upload_id)
            selected_upload = get_object_or_404(CAPADocxUpload, id=selected_upload_id, department=active_dept)
            reports = CAPAReport.objects.filter(department=active_dept, docx_upload=selected_upload)
        except ValueError:
            reports = CAPAReport.objects.filter(department=active_dept, docx_upload=None)
    else:
        reports = CAPAReport.objects.filter(department=active_dept, docx_upload=None)
        
    # Prepare records list for UI
    reports_data = []
    import random
    for r in reports:
        modified = False
        if not r.document_no:
            year = datetime.now().year
            r.document_no = f"{year}/DOC-{random.randint(100, 999)}/{active_dept.code}"
            modified = True
        if not r.issue_no:
            r.issue_no = str(random.randint(1, 12))
            modified = True
        if not r.issue_date:
            r.issue_date = r.date_incident or datetime.now().strftime('%d.%m.%Y')
            modified = True
        if modified:
            r.save()
            
        # Build structure for rowspan logic if needed, or simply flat display of actions
        reports_data.append({
            'record': r,
            'corrective_actions': r.corrective_actions if isinstance(r.corrective_actions, list) else [],
            'preventive_actions': r.preventive_actions if isinstance(r.preventive_actions, list) else [],
            'responsible_team': r.responsible_team if isinstance(r.responsible_team, list) else [],
        })
        
    context = {
        'active_dept_id': dept_id,
        'active_dept': active_dept,
        'active_module': 'CAPA',
        'active_tab': 'report',
        'reports_data': reports_data,
        'uploads': uploads,
        'selected_upload_id': selected_upload_id,
        'selected_upload': selected_upload,
        'can_edit': True,
    }
    return render(request, 'capa/report.html', context)

@login_required
@dept_visibility_required
@module_access_required('CAPA')
def capa_history(request, dept_id):
    active_dept = get_object_or_404(Department, id=dept_id)
    
    # Query uploads annotated with record counts
    uploaded_files = CAPADocxUpload.objects.filter(department=active_dept, is_manual=False).annotate(
        num_records=Count('reports')
    ).select_related('uploaded_by').order_by('-uploaded_at')
    
    # Query manually created sheets
    manual_sheets = CAPADocxUpload.objects.filter(department=active_dept, is_manual=True).annotate(
        num_records=Count('reports')
    ).select_related('uploaded_by').order_by('-uploaded_at')
    
    # Default manual records (unsorted)
    manual_count = CAPAReport.objects.filter(department=active_dept, docx_upload=None).count()
    
    context = {
        'active_dept_id': dept_id,
        'active_dept': active_dept,
        'active_module': 'CAPA',
        'active_tab': 'history',
        'uploaded_files': uploaded_files,
        'manual_sheets': manual_sheets,
        'manual_count': manual_count,
    }
    return render(request, 'capa/history.html', context)

@login_required
@require_POST
@dept_visibility_required
@module_access_required('CAPA')
def save_capa(request, dept_id, record_id=None):
    active_dept = get_object_or_404(Department, id=dept_id)
    
    if record_id:
        report = get_object_or_404(CAPAReport, id=record_id, department=active_dept)
    else:
        report = CAPAReport(department=active_dept, created_by=request.user)
        
    # File Association / Target File
    association_type = request.POST.get('association_type', 'default')
    
    if not record_id:
        if association_type == 'new':
            new_file_name = request.POST.get('new_file_name', '').strip()
            if not new_file_name:
                new_file_name = f"CAPA Manual Entry Sheet {datetime.now().strftime('%d.%m.%Y')}"
            upload = CAPADocxUpload.objects.create(
                department=active_dept,
                filename=new_file_name,
                upload_date=datetime.now().date(),
                uploaded_by=request.user,
                is_manual=True
            )
            report.docx_upload = upload
        elif association_type == 'existing':
            existing_file_id = request.POST.get('existing_file_id', '').strip()
            if existing_file_id:
                try:
                    upload = CAPADocxUpload.objects.get(id=int(existing_file_id), department=active_dept)
                    report.docx_upload = upload
                except (ValueError, CAPADocxUpload.DoesNotExist):
                    pass
        else:
            report.docx_upload = None

    # Retrieve parameters
    report.area_section = request.POST.get('area_section', '').strip()
    report.date_incident = request.POST.get('date_incident', '').strip()
    report.capa_no = request.POST.get('capa_no', '').strip()
    report.status = request.POST.get('status', 'Open').strip()
    report.document_no = request.POST.get('document_no', '').strip()
    report.issue_no = request.POST.get('issue_no', '').strip()
    report.issue_date = request.POST.get('issue_date', '').strip()
    
    # 1. Problem description
    report.problem_what = request.POST.get('problem_what', '').strip()
    report.problem_where = request.POST.get('problem_where', '').strip()
    report.problem_when = request.POST.get('problem_when', '').strip()
    report.problem_extent = request.POST.get('problem_extent', '').strip()
    
    # Breakdown details
    report.breakdown_applicable = request.POST.get('breakdown_applicable', '').strip()
    report.breakdown_hrs = request.POST.get('breakdown_hrs', '').strip()
    report.breakdown_from = request.POST.get('breakdown_from', '').strip()
    report.breakdown_to = request.POST.get('breakdown_to', '').strip()
    
    # 2. Responsible Team (dynamic list)
    t_names = request.POST.getlist('t_name')
    t_roles = request.POST.getlist('t_role')
    t_contacts = request.POST.getlist('t_contact')
    
    team_data = []
    for idx in range(len(t_names)):
        if t_names[idx].strip():
            team_data.append({
                'name': t_names[idx].strip(),
                'role': t_roles[idx].strip() if idx < len(t_roles) else '',
                'contact': t_contacts[idx].strip() if idx < len(t_contacts) else '',
            })
    report.responsible_team = team_data
    
    # 3. Correction / Immediate Actions
    report.immediate_action = request.POST.get('immediate_action', '').strip()
    report.action_timeframe = request.POST.get('action_timeframe', '').strip()
    report.action_responsibility = request.POST.get('action_responsibility', '').strip()
    
    # 4. Root Cause
    report.why_1 = request.POST.get('why_1', '').strip()
    report.why_2 = request.POST.get('why_2', '').strip()
    report.why_3 = request.POST.get('why_3', '').strip()
    report.why_4 = request.POST.get('why_4', '').strip()
    report.why_5 = request.POST.get('why_5', '').strip()
    
    report.conclusion = request.POST.get('conclusion', '').strip()
    report.five_m_applicable = request.POST.getlist('five_m_applicable')
    
    # 5. Corrective actions
    c_actions = request.POST.getlist('c_action')
    c_resps = request.POST.getlist('c_responsibility')
    c_targets = request.POST.getlist('c_target_date')
    c_impls = request.POST.getlist('c_impl_date')
    
    corr_data = []
    for idx in range(len(c_actions)):
        if c_actions[idx].strip():
            corr_data.append({
                'action': c_actions[idx].strip(),
                'responsibility': c_resps[idx].strip() if idx < len(c_resps) else '',
                'target_date': c_targets[idx].strip() if idx < len(c_targets) else '',
                'impl_date': c_impls[idx].strip() if idx < len(c_impls) else '',
            })
    report.corrective_actions = corr_data
    
    # 6. Preventive actions
    p_actions = request.POST.getlist('p_action')
    p_resps = request.POST.getlist('p_responsibility')
    p_targets = request.POST.getlist('p_target_date')
    p_impls = request.POST.getlist('p_impl_date')
    
    prev_data = []
    for idx in range(len(p_actions)):
        if p_actions[idx].strip():
            prev_data.append({
                'action': p_actions[idx].strip(),
                'responsibility': p_resps[idx].strip() if idx < len(p_resps) else '',
                'target_date': p_targets[idx].strip() if idx < len(p_targets) else '',
                'impl_date': p_impls[idx].strip() if idx < len(p_impls) else '',
            })
    report.preventive_actions = prev_data
    
    # Detailed plan, Modified documents, training, approvals
    report.detailed_plan = request.POST.get('detailed_plan', '').strip()
    report.modified_documents = request.POST.getlist('modified_documents')
    report.modified_documents_other = request.POST.get('modified_documents_other', '').strip()
    report.training_details = request.POST.get('training_details', '').strip()
    report.date_implementation = request.POST.get('date_implementation', '').strip()
    report.effectiveness_evaluation = request.POST.get('effectiveness_evaluation', '').strip()
    
    report.prepared_by = request.POST.get('prepared_by', '').strip()
    report.reviewed_by = request.POST.get('reviewed_by', '').strip()
    report.approved_by = request.POST.get('approved_by', '').strip()
    
    report.save()
    messages.success(request, f"CAPA Report {report.capa_no} saved successfully.")
    
    if report.docx_upload:
        return redirect(reverse('capa:report', args=[dept_id]) + f'?upload_id={report.docx_upload.id}')
    else:
        return redirect('capa:report', dept_id=dept_id)

@login_required
@dept_visibility_required
@module_access_required('CAPA')
def upload_file(request, dept_id):
    active_dept = get_object_or_404(Department, id=dept_id)
    if request.method != 'POST' or 'capa_file' not in request.FILES:
        messages.error(request, "Please select a valid document (.docx, .doc, .pdf) file to upload.")
        return redirect('capa:report', dept_id=dept_id)
        
    capa_file = request.FILES['capa_file']
    try:
        parsed_data = parse_capa_file(capa_file, capa_file.name)
    except Exception as e:
        messages.error(request, f"Failed to parse uploaded document: {str(e)}")
        return redirect('capa:report', dept_id=dept_id)
        
    # Save the upload reference
    upload = CAPADocxUpload.objects.create(
        department=active_dept,
        filename=capa_file.name,
        upload_date=datetime.now().date(),
        uploaded_by=request.user,
        is_manual=False
    )
    
    # Save the parsed CAPA record
    report = CAPAReport(
        department=active_dept,
        docx_upload=upload,
        created_by=request.user,
        **parsed_data
    )
    import random
    if not report.document_no:
        year = datetime.now().year
        report.document_no = f"{year}/DOC-{random.randint(100, 999)}/{active_dept.code}"
    if not report.issue_no:
        report.issue_no = str(random.randint(1, 12))
    if not report.issue_date:
        report.issue_date = parsed_data.get('issue_date') or parsed_data.get('date_incident') or datetime.now().strftime('%d.%m.%Y')
    report.save()
    
    messages.success(request, f"Successfully parsed and created CAPA report from {capa_file.name}.")
    return redirect(reverse('capa:report', args=[dept_id]) + f'?upload_id={upload.id}')

@login_required
@dept_visibility_required
@module_access_required('CAPA')
def delete_upload(request, dept_id, upload_id):
    active_dept = get_object_or_404(Department, id=dept_id)
    upload = get_object_or_404(CAPADocxUpload, id=upload_id, department=active_dept)
    
    filename = upload.filename
    upload.delete() # cascading deletes associated CAPAReport records
    messages.success(request, f"File upload '{filename}' successfully deleted.")
    return redirect('capa:history', dept_id=dept_id)

@login_required
@dept_visibility_required
@module_access_required('CAPA')
def download_pdf(request, dept_id, capa_id):
    active_dept = get_object_or_404(Department, id=dept_id)
    report = get_object_or_404(CAPAReport, id=capa_id, department=active_dept)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='CAPATitle',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        alignment=1,
        textColor=colors.black
    )
    hdr_meta_style = ParagraphStyle(
        name='CAPAHdrMeta',
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=0
    )
    section_title_style = ParagraphStyle(
        name='CAPASectionTitle',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.black,
        spaceBefore=4,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        name='CAPABody',
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.black
    )
    body_bold_style = ParagraphStyle(
        name='CAPABodyBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.black
    )
    
    def check_box(label, checked):
        tick = "Y" if checked else " "
        return f"[{tick}] {label}"
        
    story = []
    
    doc_no_val = report.document_no or "F-01(10.2.0-01)"
    issue_no_val = report.issue_no or "8"
    issue_date_val = report.issue_date or "19.11.2025"
    
    header_data = [
        [
            Paragraph(f"Document No. {doc_no_val}<br/>Issue No. {issue_no_val}<br/>Issue Date {issue_date_val}", hdr_meta_style),
            Paragraph("JINDAL STEEL LIMITED, RAIGARH<br/><br/>Corrective and Preventive Action Report", title_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[150, 373])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBEFORE', (1, 0), (1, 0), 1, colors.black),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    
    meta_data = [
        [
            Paragraph("<b>Department:</b> " + (report.department.name if report.department else ""), body_style),
            Paragraph("<b>Area / Section:</b> " + report.area_section, body_style)
        ],
        [
            Paragraph("<b>Date of Incident:</b> " + report.date_incident, body_style),
            Paragraph("<b>CAPA No:</b> " + report.capa_no, body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[261, 262])
    meta_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))
    
    b_cat_1 = check_box(">= 4 Hrs.", report.breakdown_applicable == ">= 4 Hrs." or report.breakdown_applicable == "≥ 4 Hrs.")
    b_cat_2 = check_box("2 - 4 Hrs.", report.breakdown_applicable == "2 - 4 Hrs." or report.breakdown_applicable == "2 – 4 Hrs.")
    b_cat_3 = check_box("1 - 2 Hrs.", report.breakdown_applicable == "1 - 2 Hrs." or report.breakdown_applicable == "1 – 2 Hrs.")
    b_cat_4 = check_box("<= 1 Hrs.", report.breakdown_applicable == "<= 1 Hrs." or report.breakdown_applicable == "≤ 1 Hrs.")
    checkboxes_str = f"{b_cat_1}     {b_cat_2}     {b_cat_3}     {b_cat_4}"
    
    prob_data = [
        [Paragraph("<b>1. Problem description (what/where/when/how extensive?)</b>", section_title_style), ""],
        [Paragraph("<b>What:</b>", body_bold_style), Paragraph(report.problem_what, body_style)],
        [Paragraph("<b>Where:</b>", body_bold_style), Paragraph(report.problem_where, body_style)],
        [Paragraph("<b>When:</b>", body_bold_style), Paragraph(report.problem_when, body_style)],
        [Paragraph("<b>Extent:</b>", body_bold_style), Paragraph(report.problem_extent, body_style)],
        [
            Paragraph("<b>Request to Please Tick (Y / N)<br/>the duration of breakdown,<br/>which is applicable:</b>", body_style),
            Paragraph(checkboxes_str, body_bold_style)
        ],
        [
            Paragraph("<b>In Case of Breakdown:</b>", body_bold_style),
            Paragraph(f"Duration of Breakdown (Hrs.): <b>{report.breakdown_hrs}</b>   From (Time): <b>{report.breakdown_from}</b>   To (time): <b>{report.breakdown_to}</b>", body_style)
        ]
    ]
    prob_table = Table(prob_data, colWidths=[150, 373])
    prob_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (0, 0), (1, 0)),
        ('LINEBELOW', (0, 0), (1, 0), 1, colors.black),
        ('INNERGRID', (0, 1), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(prob_table)
    story.append(Spacer(1, 8))
    
    team_rows = [
        [
            Paragraph("<b>Role Designation</b>", body_bold_style),
            Paragraph("<b>Team Member Name</b>", body_bold_style),
            Paragraph("<b>Role / Function</b>", body_bold_style),
            Paragraph("<b>Contact No</b>", body_bold_style)
        ]
    ]
    for idx in range(3):
        member = {}
        if idx < len(report.responsible_team):
            member = report.responsible_team[idx]
        role_lbl = "Team Leader" if idx == 0 else f"Team Member {idx}"
        team_rows.append([
            Paragraph(role_lbl, body_bold_style),
            Paragraph(member.get('name', ''), body_style),
            Paragraph(member.get('role', ''), body_style),
            Paragraph(member.get('contact', ''), body_style)
        ])
    team_table = Table(team_rows, colWidths=[130, 150, 140, 103])
    team_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F0FA')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("<b>2. Responsible Team for Corrective/Preventive Actions:</b>", section_title_style))
    story.append(team_table)
    story.append(Spacer(1, 8))
    
    corr_imm_data = [
        [Paragraph("<b>3. Correction/ Immediate Actions taken:</b>", section_title_style), ""],
        [Paragraph(report.immediate_action, body_style), ""],
        [
            Paragraph("<b>Time Frame:</b> " + report.action_timeframe, body_style),
            Paragraph("<b>Responsibility:</b> " + report.action_responsibility, body_style)
        ]
    ]
    corr_imm_table = Table(corr_imm_data, colWidths=[261, 262])
    corr_imm_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        ('LINEBELOW', (0, 0), (1, 0), 1, colors.black),
        ('LINEBELOW', (0, 1), (1, 1), 0.5, colors.black),
        ('LINEBEFORE', (1, 2), (1, 2), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(corr_imm_table)
    
    # ------------------ PAGE 2 ------------------
    story.append(PageBreak())
    
    story.append(Paragraph("<b>4. Root cause analysis - Analysis finding:</b>", section_title_style))
    
    # 5M ticks
    m_mat = check_box("1M Material", "1M Material" in report.five_m_applicable)
    m_man = check_box("2M Man", "2M Man" in report.five_m_applicable)
    m_mac = check_box("3M Machine", "3M Machine" in report.five_m_applicable)
    m_mea = check_box("4M Measure", "4M Measure" in report.five_m_applicable)
    m_met = check_box("5M Method", "5M Method" in report.five_m_applicable)
    five_ms_str = f"<b>Applicable 5 M's (Tick):</b><br/>{m_mat}<br/>{m_man}<br/>{m_mac}<br/>{m_mea}<br/>{m_met}"
    
    why_data = [
        [Paragraph("<b>1st Why:</b>", body_bold_style), Paragraph(report.why_1, body_style), Paragraph(five_ms_str, body_style)],
        [Paragraph("<b>2nd Why:</b>", body_bold_style), Paragraph(report.why_2, body_style), ""],
        [Paragraph("<b>3rd Why:</b>", body_bold_style), Paragraph(report.why_3, body_style), ""],
        [Paragraph("<b>4th Why:</b>", body_bold_style), Paragraph(report.why_4, body_style), ""],
        [Paragraph("<b>5th Why:</b>", body_bold_style), Paragraph(report.why_5, body_style), ""]
    ]
    why_table = Table(why_data, colWidths=[60, 313, 150])
    why_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('SPAN', (2, 0), (2, 4)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(why_table)
    story.append(Spacer(1, 8))
    
    conclusion_data = [
        [Paragraph("<b>Conclusion (s):</b>", body_bold_style)],
        [Paragraph(report.conclusion, body_style)]
    ]
    conclusion_table = Table(conclusion_data, colWidths=[523])
    conclusion_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F0FA')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(conclusion_table)
    story.append(Spacer(1, 8))
    
    # 5. Corrective action(s)
    corr_rows = [
        [
            Paragraph("<b>Corrective Action(s)</b>", body_bold_style),
            Paragraph("<b>Responsibility</b>", body_bold_style),
            Paragraph("<b>Target Date</b>", body_bold_style),
            Paragraph("<b>Implementation Date</b>", body_bold_style)
        ]
    ]
    for action in report.corrective_actions:
        corr_rows.append([
            Paragraph(action.get('action', ''), body_style),
            Paragraph(action.get('responsibility', ''), body_style),
            Paragraph(action.get('target_date', ''), body_style),
            Paragraph(action.get('impl_date', ''), body_style)
        ])
    # Add empty rows if none
    if len(corr_rows) == 1:
        corr_rows.append([Paragraph("", body_style), "", "", ""])
        
    corr_table = Table(corr_rows, colWidths=[243, 100, 80, 100])
    corr_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F0FA')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("<b>5. Recommended Corrective action(s):</b>", section_title_style))
    story.append(corr_table)
    story.append(Spacer(1, 8))
    
    # 6. Preventive action(s)
    prev_rows = [
        [
            Paragraph("<b>Preventive Action(s)</b>", body_bold_style),
            Paragraph("<b>Responsibility</b>", body_bold_style),
            Paragraph("<b>Target Date</b>", body_bold_style),
            Paragraph("<b>Implementation Date</b>", body_bold_style)
        ]
    ]
    for action in report.preventive_actions:
        prev_rows.append([
            Paragraph(action.get('action', ''), body_style),
            Paragraph(action.get('responsibility', ''), body_style),
            Paragraph(action.get('target_date', ''), body_style),
            Paragraph(action.get('impl_date', ''), body_style)
        ])
    if len(prev_rows) == 1:
        prev_rows.append([Paragraph("", body_style), "", "", ""])
        
    prev_table = Table(prev_rows, colWidths=[243, 100, 80, 100])
    prev_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F0FA')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("<b>6. Recommended Preventive action(s):</b>", section_title_style))
    story.append(prev_table)
    
    # ------------------ PAGE 3 ------------------
    story.append(PageBreak())
    
    plan_data = [
        [Paragraph("<b>7. Detailed Implementation Plan:</b>", section_title_style)],
        [Paragraph(report.detailed_plan, body_style)]
    ]
    plan_table = Table(plan_data, colWidths=[523])
    plan_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F0FA')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(plan_table)
    story.append(Spacer(1, 8))
    
    # Documents ticks
    doc_moc = check_box("MOC", "MOC" in report.modified_documents)
    doc_sop = check_box("SOP / SMP", "SOP / SMP" in report.modified_documents)
    doc_risk = check_box("Risk and Opportunity Register", "Risk and Opportunity Register" in report.modified_documents)
    doc_env = check_box("Register of Environmental Aspect Impact", "Register of Environmental Aspect Impact and OH & S Risks" in report.modified_documents)
    doc_train = check_box("Training Need Identification", "Training Need Identification" in report.modified_documents)
    docs_checkboxes = f"{doc_moc}    {doc_sop}    {doc_risk}<br/>{doc_env}<br/>{doc_train}<br/><b>Others:</b> {report.modified_documents_other}"
    
    doc_train_data = [
        [
            Paragraph("<b>8. Modified documents (Please Tick in the applicable document):</b>", body_bold_style),
            Paragraph(docs_checkboxes, body_style)
        ],
        [
            Paragraph("<b>9. Training Details (If any):</b>", body_bold_style),
            Paragraph(report.training_details, body_style)
        ],
        [
            Paragraph("<b>10. Date of Implementation:</b>", body_bold_style),
            Paragraph(report.date_implementation, body_style)
        ]
    ]
    doc_train_table = Table(doc_train_data, colWidths=[200, 323])
    doc_train_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("<b>8. Modified documents & 9. Training & 10. Date of Implementation:</b>", section_title_style))
    story.append(doc_train_table)
    story.append(Spacer(1, 8))
    
    eff_data = [
        [Paragraph("<b>11. Effectiveness evaluation of implemented Correction, Corrective Action / Preventive Action</b>", section_title_style)],
        [Paragraph(report.effectiveness_evaluation, body_style)]
    ]
    eff_table = Table(eff_data, colWidths=[523])
    eff_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F0FA')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(eff_table)
    story.append(Spacer(1, 15))
    
    # Approvals sign-offs
    appr_data = [
        [
            Paragraph("<b>Prepared By</b><br/>(Name and Signature of Initiator)", body_bold_style),
            Paragraph("<b>Reviewed By</b><br/>(Name and Signature of Reviewer)", body_bold_style),
            Paragraph("<b>Approved by</b><br/>(Name and Signature of HOD)", body_bold_style)
        ],
        [
            Paragraph("<br/><b>" + report.prepared_by + "</b>", body_style),
            Paragraph("<br/><b>" + report.reviewed_by + "</b>", body_style),
            Paragraph("<br/><b>" + report.approved_by + "</b>", body_style)
        ]
    ]
    appr_table = Table(appr_data, colWidths=[174, 174, 175])
    appr_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(appr_table)
    
    doc.build(story)
    
    pdf_val = buffer.getvalue()
    buffer.close()
    
    filename = f"CAPA_{report.capa_no or 'Draft'}_{active_dept.code}.pdf"
    response = HttpResponse(pdf_val, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
