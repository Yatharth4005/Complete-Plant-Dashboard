import os
import io
import json
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.conf import settings

from tpm.models import Department, KaizenSheet
from tpm.utils.decorators import dept_access_required

import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as ReportLabImage, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

@login_required
@dept_access_required
def kaizen_list_partial(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    sheets = KaizenSheet.objects.filter(department=dept, pillar=pillar_id).order_by('-created_at')
    
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'sheets': sheets,
    }
    return render(request, 'partials/_kaizen_list.html', context)

@login_required
@dept_access_required
def kaizen_edit_partial(request, dept_id, pillar_id, kaizen_id=None):
    dept = get_object_or_404(Department, id=dept_id)
    kaizen = None
    if kaizen_id:
        kaizen = get_object_or_404(KaizenSheet, id=kaizen_id, department=dept, pillar=pillar_id)
        
    # Auto-prefill variables for new sheets
    prefills = {
        'kaizen_no': f"K-{(kaizen.id if kaizen else KaizenSheet.objects.count() + 1):03d}",
        'activities': [pillar_id],
        'result_areas': [],
        'team_members': ['', '', '', ''],
        'tangible_benefits': ['', '', '', '', ''],
        'intangible_benefits': ['', '', '', '', ''],
        'horizontal_deployment': [
            {'sl_no': '1', 'area_equip': '', 'target_date': '', 'responsibility': '', 'status': 'Pending'},
            {'sl_no': '2', 'area_equip': '', 'target_date': '', 'responsibility': '', 'status': 'Pending'},
            {'sl_no': '3', 'area_equip': '', 'target_date': '', 'responsibility': '', 'status': 'Pending'},
        ]
    }
    
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'kaizen': kaizen,
        'prefills': prefills,
    }
    return render(request, 'partials/_kaizen_form.html', context)

@login_required
@dept_access_required
@require_POST
def kaizen_save(request, dept_id, pillar_id, kaizen_id=None):
    dept = get_object_or_404(Department, id=dept_id)
    
    if kaizen_id:
        kaizen = get_object_or_404(KaizenSheet, id=kaizen_id, department=dept, pillar=pillar_id)
    else:
        kaizen = KaizenSheet(department=dept, pillar=pillar_id, created_by=request.user)
        
    # Standard text fields
    kaizen.kaizen_no = request.POST.get('kaizen_no', '').strip()
    kaizen.loss_name = request.POST.get('loss_name', '').strip()
    kaizen.area_equipment = request.POST.get('area_equipment', '').strip()
    kaizen.circle_name = request.POST.get('circle_name', '').strip()
    kaizen.theme = request.POST.get('theme', '').strip()
    kaizen.idea = request.POST.get('idea', '').strip()
    kaizen.benchmark = request.POST.get('benchmark', '').strip()
    kaizen.target = request.POST.get('target', '').strip()
    kaizen.start_date = request.POST.get('start_date', '').strip()
    kaizen.finish_date = request.POST.get('finish_date', '').strip()
    kaizen.team_leader = request.POST.get('team_leader', '').strip()
    kaizen.analysis = request.POST.get('analysis', '').strip()
    kaizen.result_text = request.POST.get('result_text', '').strip()
    
    # Checkboxes: Activities & Result Areas
    kaizen.activities = request.POST.getlist('activities')
    kaizen.result_areas = request.POST.getlist('result_areas')
    
    # JSON lists: Team Members
    members = [
        request.POST.get('member_1', '').strip(),
        request.POST.get('member_2', '').strip(),
        request.POST.get('member_3', '').strip(),
        request.POST.get('member_4', '').strip(),
    ]
    kaizen.team_members = [m for m in members if m]
    
    # Tangible & Intangible benefits lists
    tangibles = [
        request.POST.get('tangible_1', '').strip(),
        request.POST.get('tangible_2', '').strip(),
        request.POST.get('tangible_3', '').strip(),
        request.POST.get('tangible_4', '').strip(),
        request.POST.get('tangible_5', '').strip(),
    ]
    kaizen.tangible_benefits = [t for t in tangibles if t]
    
    intangibles = [
        request.POST.get('intangible_1', '').strip(),
        request.POST.get('intangible_2', '').strip(),
        request.POST.get('intangible_3', '').strip(),
        request.POST.get('intangible_4', '').strip(),
        request.POST.get('intangible_5', '').strip(),
    ]
    kaizen.intangible_benefits = [i for i in intangibles if i]
    
    # Horizontal deployment list from form dynamic inputs
    h_sl = request.POST.getlist('h_sl_no')
    h_area = request.POST.getlist('h_area_equip')
    h_date = request.POST.getlist('h_target_date')
    h_resp = request.POST.getlist('h_responsibility')
    h_stat = request.POST.getlist('h_status')
    
    deployment_data = []
    for idx in range(len(h_sl)):
        # Make sure there is at least some text filled
        if h_area[idx].strip() or h_resp[idx].strip():
            deployment_data.append({
                'sl_no': h_sl[idx].strip() or str(idx + 1),
                'area_equip': h_area[idx].strip(),
                'target_date': h_date[idx].strip(),
                'responsibility': h_resp[idx].strip(),
                'status': h_stat[idx].strip() or 'Pending',
            })
    kaizen.horizontal_deployment = deployment_data
    
    # Image uploads
    if 'before_image' in request.FILES:
        kaizen.before_image = request.FILES['before_image']
    if 'after_image' in request.FILES:
        kaizen.after_image = request.FILES['after_image']
    if 'result_image' in request.FILES:
        kaizen.result_image = request.FILES['result_image']
        
    kaizen.save()
    
    return HttpResponse(
        status=204,
        headers={
            'HX-Trigger': 'kaizenListChanged'
        }
    )

@login_required
@dept_access_required
@require_POST
def kaizen_delete(request, dept_id, pillar_id, kaizen_id):
    dept = get_object_or_404(Department, id=dept_id)
    kaizen = get_object_or_404(KaizenSheet, id=kaizen_id, department=dept, pillar=pillar_id)
    kaizen.delete()
    return kaizen_list_partial(request, dept_id, pillar_id)

@login_required
def download_excel(request, kaizen_id):
    kaizen = get_object_or_404(KaizenSheet, id=kaizen_id)
    
    wb_content = generate_kaizen_excel(kaizen)
    
    filename = f"KAIZEN_{kaizen.kaizen_no or 'Draft'}_{kaizen.pillar}.xlsx"
    response = HttpResponse(
        wb_content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def download_pdf(request, kaizen_id):
    kaizen = get_object_or_404(KaizenSheet, id=kaizen_id)
    
    pdf_content = generate_kaizen_pdf(kaizen)
    
    filename = f"KAIZEN_{kaizen.kaizen_no or 'Draft'}_{kaizen.pillar}.pdf"
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_kaizen_excel(kaizen):
    template_path = os.path.join(settings.BASE_DIR, 'KAIZEN - Blank Format.xlsx')
    if not os.path.exists(template_path):
        template_path = os.path.join(settings.BASE_DIR.parent, 'TPM Portal', 'KAIZEN - Blank Format.xlsx')
        
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active
    
    # Fill Kaizen No
    ws.cell(row=3, column=2, value=f"KAIZEN NO.  {kaizen.kaizen_no}")
    
    # Fill Activity checklist
    activity_cols = {
        'KK': 7, 'JH': 8, 'QM': 9, 'PM': 10, 'SHE': 11, 'OTPM': 12, 'DM': 13, 'ET': 14
    }
    for act, col in activity_cols.items():
        val = act
        if act in kaizen.activities:
            val = f"✓ {act}"
        ws.cell(row=3, column=col, value=val)
        
    # Loss Name
    ws.cell(row=4, column=7, value=kaizen.loss_name)
    
    # Result Area checklist
    result_cols = {
        'S': 7, 'Q': 9, 'P': 10, 'C': 11, 'D': 12, 'M': 13
    }
    for res, col in result_cols.items():
        val = res
        if res in kaizen.result_areas:
            val = f"✓ {res}"
        ws.cell(row=5, column=col, value=val)
        
    # Department, Area, Circle Name
    ws.cell(row=6, column=2, value=f"DEPARTMENT :  {kaizen.department.name}")
    ws.cell(row=6, column=6, value=f"AREA/EQUIPMENT :  {kaizen.area_equipment}")
    ws.cell(row=6, column=10, value=f"TPM CIRCLE NAME:  {kaizen.circle_name}")
    
    # Theme & Idea
    ws.cell(row=10, column=2, value=kaizen.theme)
    ws.cell(row=10, column=6, value=kaizen.idea)
    
    # Benchmark, Target, Start, Finish
    ws.cell(row=8, column=12, value=kaizen.benchmark)
    ws.cell(row=9, column=12, value=kaizen.target)
    ws.cell(row=10, column=12, value=kaizen.start_date)
    ws.cell(row=11, column=12, value=kaizen.finish_date)
    
    # Team Members
    ws.cell(row=13, column=12, value=kaizen.team_leader)
    members = kaizen.team_members
    for idx in range(4):
        val = members[idx] if idx < len(members) else ""
        ws.cell(row=14 + idx, column=12, value=val)
        
    # Benefits: Tangible
    tangible = kaizen.tangible_benefits
    for idx in range(5):
        val = tangible[idx] if idx < len(tangible) else ""
        ws.cell(row=20 + idx, column=11, value=val)
        
    # Benefits: Intangible
    intangible = kaizen.intangible_benefits
    for idx in range(5):
        val = intangible[idx] if idx < len(intangible) else ""
        ws.cell(row=26 + idx, column=11, value=val)
        
    # Analysis & Result Text
    ws.cell(row=32, column=2, value=kaizen.analysis)
    ws.cell(row=32, column=6, value=kaizen.result_text)
    
    # Horizontal Deployment
    deployment = kaizen.horizontal_deployment
    for idx in range(3):
        row_idx = 35 + idx # Row index 35 corresponds to row 36 (1-based: Row 35, Col 10, Col 11)
        # Let's adjust based on grid: Row 35, Col 10 is SL. NO. 1
        if idx < len(deployment):
            item = deployment[idx]
            ws.cell(row=row_idx, column=10, value=item.get('sl_no', str(idx+1)))
            ws.cell(row=row_idx, column=11, value=item.get('area_equip', ''))
            ws.cell(row=row_idx, column=12, value=item.get('target_date', ''))
            ws.cell(row=row_idx, column=14, value=item.get('responsibility', ''))
            ws.cell(row=row_idx, column=16, value=item.get('status', ''))
            
    # Add Images (Before, After, Result Graph)
    if kaizen.before_image:
        try:
            img_path = kaizen.before_image.path
            img = OpenpyxlImage(img_path)
            img.width = 240
            img.height = 185
            ws.add_image(img, 'B19')
        except Exception as e:
            print(f"Error adding before image: {e}")
            
    if kaizen.after_image:
        try:
            img_path = kaizen.after_image.path
            img = OpenpyxlImage(img_path)
            img.width = 240
            img.height = 185
            ws.add_image(img, 'F19')
        except Exception as e:
            print(f"Error adding after image: {e}")
            
    if kaizen.result_image:
        try:
            img_path = kaizen.result_image.path
            img = OpenpyxlImage(img_path)
            img.width = 240
            img.height = 115
            ws.add_image(img, 'F32')
        except Exception as e:
            print(f"Error adding result image: {e}")
            
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_kaizen_pdf(kaizen):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20
    )
    
    # col widths to sum to 555 (A4 is 595 width, 20 margin each side)
    col_widths = [15, 60, 45, 45, 45, 80, 20, 20, 20, 40, 30, 30, 30, 30, 45, 45]
    
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle('Cell', fontName='Helvetica', fontSize=7, leading=8, textColor=colors.HexColor('#1A2640'))
    cell_style_bold = ParagraphStyle('CellBold', fontName='Helvetica-Bold', fontSize=7, leading=8, textColor=colors.HexColor('#1A2640'))
    cell_style_center = ParagraphStyle('CellCenter', fontName='Helvetica', fontSize=7, leading=8, textColor=colors.HexColor('#1A2640'), alignment=1)
    cell_style_center_bold = ParagraphStyle('CellCenterBold', fontName='Helvetica-Bold', fontSize=7, leading=8, textColor=colors.HexColor('#1A2640'), alignment=1)
    
    grid = [[Paragraph("", cell_style) for _ in range(16)] for _ in range(39)]
    
    # 1. KAIZEN NO.
    grid[2][1] = Paragraph(f"<b>KAIZEN NO.</b><br/>{kaizen.kaizen_no}", cell_style_center)
    
    # 2. Title
    grid[2][2] = Paragraph("<b>KAIZEN IDEA SHEET</b>", ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=1, textColor=colors.HexColor('#003478')))
    
    # 3. Activity list
    grid[2][5] = Paragraph("<b>ACTIVITY</b>", cell_style_center_bold)
    activities_list = ['KK', 'JH', 'QM', 'PM', 'SHE', 'OTPM', 'DM', 'ET']
    for idx, act in enumerate(activities_list):
        checked = "✓" if act in kaizen.activities else ""
        grid[2][6 + idx] = Paragraph(f"<b>{act}</b><br/>{checked}", cell_style_center)
        
    # 4. Loss Name
    grid[3][5] = Paragraph("<b>Loss Name/JH STEP (if Any)</b>", cell_style_bold)
    grid[3][6] = Paragraph(kaizen.loss_name, cell_style)
    
    # 5. Result Area
    grid[4][5] = Paragraph("<b>RESULT AREA</b>", cell_style_bold)
    result_areas_list = ['S', 'Q', 'P', 'C', 'D', 'M']
    res_indices = {'S': 6, 'Q': 8, 'P': 9, 'C': 10, 'D': 11, 'M': 12}
    for res in result_areas_list:
        checked = "✓" if res in kaizen.result_areas else ""
        col_idx = res_indices[res]
        grid[4][col_idx] = Paragraph(f"<b>{res}</b><br/>{checked}", cell_style_center)
        
    # 6. Dept, Area, Circle Name
    grid[5][1] = Paragraph(f"<b>DEPARTMENT :</b> {kaizen.department.name}", cell_style)
    grid[5][5] = Paragraph(f"<b>AREA/EQUIPMENT :</b> {kaizen.area_equipment}", cell_style)
    grid[5][9] = Paragraph(f"<b>TPM CIRCLE NAME:</b> {kaizen.circle_name}", cell_style)
    
    # 7. Theme & Idea
    grid[7][1] = Paragraph("<b>KAIZEN THEME</b>", cell_style_bold)
    grid[9][1] = Paragraph(kaizen.theme, cell_style)
    
    grid[7][5] = Paragraph("<b>IDEA</b>", cell_style_bold)
    grid[9][5] = Paragraph(kaizen.idea, cell_style)
    
    # 8. Target parameters
    grid[7][9] = Paragraph("<b>BENCHMARK</b>", cell_style_bold)
    grid[7][11] = Paragraph(kaizen.benchmark, cell_style)
    
    grid[8][9] = Paragraph("<b>TARGET</b>", cell_style_bold)
    grid[8][11] = Paragraph(kaizen.target, cell_style)
    
    grid[9][9] = Paragraph("<b>KAIZEN START</b>", cell_style_bold)
    grid[9][11] = Paragraph(kaizen.start_date, cell_style)
    
    grid[10][9] = Paragraph("<b>KAIZEN FINISH</b>", cell_style_bold)
    grid[10][11] = Paragraph(kaizen.finish_date, cell_style)
    
    # Team members
    grid[11][9] = Paragraph("<b>TEAM MEMBERS</b>", cell_style_center_bold)
    
    grid[12][9] = Paragraph("<b>LEADER</b>", cell_style_bold)
    grid[12][11] = Paragraph(kaizen.team_leader, cell_style)
    
    members = kaizen.team_members
    for idx in range(4):
        grid[13 + idx][9] = Paragraph("<b>MEMBER</b>", cell_style_bold)
        val = members[idx] if idx < len(members) else ""
        grid[13 + idx][11] = Paragraph(val, cell_style)
        
    # Before/After headers
    grid[17][1] = Paragraph("<b>BEFORE</b>", cell_style_center_bold)
    grid[17][5] = Paragraph("<b>AFTER</b>", cell_style_center_bold)
    
    # Before/After images
    if kaizen.before_image:
        try:
            grid[18][1] = ReportLabImage(kaizen.before_image.path, width=140, height=120)
        except:
            grid[18][1] = Paragraph("[Image Error]", cell_style_center)
    else:
        grid[18][1] = Paragraph("(ILLUSTRATE WITH PHOTO/SKETCH)", cell_style_center)
        
    if kaizen.after_image:
        try:
            grid[18][5] = ReportLabImage(kaizen.after_image.path, width=140, height=120)
        except:
            grid[18][5] = Paragraph("[Image Error]", cell_style_center)
    else:
        grid[18][5] = Paragraph("(ILLUSTRATE WITH PHOTO/SKETCH)", cell_style_center)
        
    grid[28][1] = Paragraph("(ILLUSTRATE WITH PHOTO/SKETCH)", cell_style_center)
    grid[28][5] = Paragraph("(ILLUSTRATE WITH PHOTO/SKETCH)", cell_style_center)
    
    # Benefits
    grid[17][9] = Paragraph("<b>BENEFITS</b>", cell_style_center_bold)
    grid[18][9] = Paragraph("<b>TANGIBLE</b>", cell_style_bold)
    
    tangible = kaizen.tangible_benefits
    for idx in range(5):
        val = tangible[idx] if idx < len(tangible) else ""
        grid[19 + idx][9] = Paragraph(f"{idx+1}.0", cell_style_bold)
        grid[19 + idx][10] = Paragraph(val, cell_style)
        
    grid[24][9] = Paragraph("<b>INTANGIBLE</b>", cell_style_bold)
    intangible = kaizen.intangible_benefits
    for idx in range(5):
        val = intangible[idx] if idx < len(intangible) else ""
        grid[25 + idx][9] = Paragraph(f"{idx+1}.0", cell_style_bold)
        grid[25 + idx][10] = Paragraph(val, cell_style)
        
    # Analysis & Result Label
    grid[30][1] = Paragraph("<b>ANAYLSIS - </b>", cell_style_bold)
    grid[31][1] = Paragraph(kaizen.analysis, cell_style)
    
    grid[30][5] = Paragraph("<b>RESULT</b>", cell_style_bold)
    if kaizen.result_image:
        try:
            grid[31][5] = ReportLabImage(kaizen.result_image.path, width=140, height=75)
        except:
            grid[31][5] = Paragraph(kaizen.result_text, cell_style)
    else:
        grid[31][5] = Paragraph(kaizen.result_text, cell_style)
        
    grid[37][5] = Paragraph("(ILLUSTRATE WITH BAR/LINE GRAPH)", cell_style_center)
    
    # Horizontal Deployment
    grid[30][9] = Paragraph("<b>SCOPE & PLAN OF HORIZONTAL DEPLOYMENT</b>", cell_style_center_bold)
    grid[32][9] = Paragraph("<b>SL. NO.</b>", cell_style_center_bold)
    grid[32][10] = Paragraph("<b>AREA/ EQUIP NO.</b>", cell_style_center_bold)
    grid[32][11] = Paragraph("<b>TARGET DATE</b>", cell_style_center_bold)
    grid[32][13] = Paragraph("<b>RESPONSIBILITY</b>", cell_style_center_bold)
    grid[32][15] = Paragraph("<b>STATUS</b>", cell_style_center_bold)
    
    deployment = kaizen.horizontal_deployment
    for idx in range(3):
        row_idx = 35 + idx
        if idx < len(deployment):
            item = deployment[idx]
            grid[row_idx][9] = Paragraph(item.get('sl_no', str(idx+1)), cell_style_center)
            grid[row_idx][10] = Paragraph(item.get('area_equip', ''), cell_style)
            grid[row_idx][11] = Paragraph(item.get('target_date', ''), cell_style_center)
            grid[row_idx][13] = Paragraph(item.get('responsibility', ''), cell_style)
            grid[row_idx][15] = Paragraph(item.get('status', ''), cell_style_center)
            
    # Compile TableStyle spans
    table_styles = [
        ('GRID', (1,2), (-1,37), 0.5, colors.HexColor('#000000')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        
        ('SPAN', (1,2), (1,4)),   # Kaizen No
        ('SPAN', (2,2), (4,4)),   # Title
        
        ('SPAN', (7,3), (14,3)),  # Loss Name merge
        
        ('SPAN', (1,5), (4,6)),   # Dept
        ('SPAN', (5,5), (8,6)),   # Area
        ('SPAN', (9,5), (13,6)),  # Circle
        
        ('SPAN', (1,7), (4,8)),   # Theme title
        ('SPAN', (1,9), (4,16)),  # Theme body
        
        ('SPAN', (5,7), (8,8)),   # Idea title
        ('SPAN', (5,9), (8,16)),  # Idea body
        
        ('SPAN', (9,7), (10,7)),  # Bench label
        ('SPAN', (11,7), (15,7)), # Bench val
        
        ('SPAN', (9,8), (10,8)),  # Target label
        ('SPAN', (11,8), (15,8)), # Target val
        
        ('SPAN', (9,9), (10,9)),  # Start label
        ('SPAN', (11,9), (15,9)), # Start val
        
        ('SPAN', (9,10), (10,10)),# Finish label
        ('SPAN', (11,10), (15,10)),# Finish val
        
        ('SPAN', (9,11), (15,11)),# Team member header
        
        ('SPAN', (9,12), (10,12)),# Leader label
        ('SPAN', (11,12), (15,12)),# Leader val
        
        ('SPAN', (9,13), (10,13)),# Member 1 label
        ('SPAN', (11,13), (15,13)),# Member 1 val
        
        ('SPAN', (9,14), (10,14)),# Member 2 label
        ('SPAN', (11,14), (15,14)),# Member 2 val
        
        ('SPAN', (9,15), (10,15)),# Member 3 label
        ('SPAN', (11,15), (15,15)),# Member 3 val
        
        ('SPAN', (9,16), (10,16)),# Member 4 label
        ('SPAN', (11,16), (15,16)),# Member 4 val
        
        ('SPAN', (1,17), (4,17)), # Before title
        ('SPAN', (1,18), (4,27)), # Before image region
        ('SPAN', (1,28), (4,29)), # Before subtext
        
        ('SPAN', (5,17), (8,17)), # After title
        ('SPAN', (5,18), (8,27)), # After image region
        ('SPAN', (5,28), (8,29)), # After subtext
        
        ('SPAN', (9,17), (15,17)),# Benefits title
        ('SPAN', (9,18), (15,18)),# Tangible header
        
        ('SPAN', (10,19), (15,19)),# Tangible 1 val
        ('SPAN', (10,20), (15,20)),# Tangible 2 val
        ('SPAN', (10,21), (15,21)),# Tangible 3 val
        ('SPAN', (10,22), (15,22)),# Tangible 4 val
        ('SPAN', (10,23), (15,23)),# Tangible 5 val
        
        ('SPAN', (9,24), (15,24)),# Intangible header
        
        ('SPAN', (10,25), (15,25)),# Intangible 1 val
        ('SPAN', (10,26), (15,26)),# Intangible 2 val
        ('SPAN', (10,27), (15,27)),# Intangible 3 val
        ('SPAN', (10,28), (15,28)),# Intangible 4 val
        ('SPAN', (10,29), (15,29)),# Intangible 5 val
        
        ('SPAN', (1,30), (4,30)), # Analysis header
        ('SPAN', (1,31), (4,36)), # Analysis body
        
        ('SPAN', (5,30), (8,30)), # Result header
        ('SPAN', (5,31), (8,36)), # Result body
        ('SPAN', (5,37), (8,37)), # Result subtext
        
        ('SPAN', (9,30), (15,31)),# Deployment header
        
        ('SPAN', (11,32), (12,34)),# Deployment col target date span
        ('SPAN', (13,32), (14,34)),# Deployment col responsibility span
        ('SPAN', (9,32), (9,34)),  # SL no span
        ('SPAN', (10,32), (10,34)),# Area span
        ('SPAN', (15,32), (15,34)),# Status span
        
        ('SPAN', (11,35), (12,35)),# Deployment row 1 date
        ('SPAN', (13,35), (14,35)),# Deployment row 1 resp
        
        ('SPAN', (11,36), (12,36)),# Deployment row 2 date
        ('SPAN', (13,36), (14,36)),# Deployment row 2 resp
        
        ('SPAN', (11,37), (12,37)),# Deployment row 3 date
        ('SPAN', (13,37), (14,37)),# Deployment row 3 resp
    ]
    
    pdf_table = Table(grid, colWidths=col_widths, rowHeights=19)
    pdf_table.setStyle(TableStyle(table_styles))
    
    doc.build([pdf_table])
    buffer.seek(0)
    return buffer.getvalue()
