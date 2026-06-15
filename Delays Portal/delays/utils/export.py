import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.utils import timezone
from django.db.models import Sum, Avg
from delays.models import DelayRecord

def generate_delays_pdf(department):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#003478'),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#003478'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['BodyText'],
        fontSize=9,
        leading=12
    )

    table_hdr_style = ParagraphStyle(
        'TableHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )

    # Title
    story.append(Paragraph("Jindal Steel Operations Portal", title_style))
    story.append(Paragraph(f"Department: {department.name} | Delay Breakdown & Analytics Report", subtitle_style))
    story.append(Paragraph(f"Generated on: {timezone.now().strftime('%d-%b-%Y %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Query data
    records = DelayRecord.objects.filter(department=department).order_by('-date', '-id')
    total_mins = records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
    total_hrs = total_mins / 60.0
    total_events = records.count()
    
    agency_breakdown = records.values('agency').annotate(total=Sum('duration_mins')).order_by('-total')
    top_agency = agency_breakdown[0]['agency'] if agency_breakdown else "N/A"
    top_agency_mins = agency_breakdown[0]['total'] if agency_breakdown else 0.0
    
    avg_duration = records.aggregate(Avg('duration_mins'))['duration_mins__avg'] or 0.0
    
    # 1. KPI Metrics
    story.append(Paragraph("1. Executive Summary Metrics", section_style))
    kpi_data = [
        [Paragraph("Metric", table_hdr_style), Paragraph("Value", table_hdr_style), Paragraph("Description", table_hdr_style)],
        [Paragraph("Total Downtime Hours", table_cell_style), Paragraph(f"{total_hrs:.1f} hrs", table_cell_style), Paragraph(f"Accumulated breakdown duration ({total_mins:.1f} minutes)", table_cell_style)],
        [Paragraph("Downtime Events Logged", table_cell_style), Paragraph(str(total_events), table_cell_style), Paragraph("Total number of delay incidents registered", table_cell_style)],
        [Paragraph("Primary Agency Bottleneck", table_cell_style), Paragraph(f"{top_agency}", table_cell_style), Paragraph(f"Responsible for {top_agency_mins:.1f} mins of total delays", table_cell_style)],
        [Paragraph("Avg. Incident Duration", table_cell_style), Paragraph(f"{avg_duration:.1f} mins", table_cell_style), Paragraph("Mean downtime duration per delay event", table_cell_style)]
    ]
    t_kpi = Table(kpi_data, colWidths=[150, 100, 290])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003478')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1DCF0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 15))
    
    # 2. Responsible Agency Breakdown
    story.append(Paragraph("2. Responsible Agency Breakdown", section_style))
    agency_data = [[Paragraph("Agency / Responsible Body", table_hdr_style), Paragraph("Total Downtime Mins", table_hdr_style), Paragraph("Share %", table_hdr_style)]]
    for ab in agency_breakdown:
        share = (ab['total'] / total_mins * 100) if total_mins > 0 else 0.0
        agency_data.append([
            Paragraph(ab['agency'] or "N/A", table_cell_style),
            Paragraph(f"{ab['total']:.1f} mins", table_cell_style),
            Paragraph(f"{share:.1f}%", table_cell_style)
        ])
    if len(agency_data) > 1:
        t_agency = Table(agency_data, colWidths=[240, 150, 150])
        t_agency.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003478')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1DCF0')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_agency)
    else:
        story.append(Paragraph("No agency breakdown data available.", body_style))
    story.append(Spacer(1, 15))
    
    # 3. Detailed Delay Logs (Top 50)
    story.append(Paragraph("3. Detailed Delay Logs (Showing latest 50 logs)", section_style))
    log_data = [[
        Paragraph("Date", table_hdr_style),
        Paragraph("Duration (m)", table_hdr_style),
        Paragraph("Agency", table_hdr_style),
        Paragraph("Equipment", table_hdr_style),
        Paragraph("Description", table_hdr_style)
    ]]
    for r in records[:50]:
        log_data.append([
            Paragraph(r.date.strftime('%Y-%m-%d'), table_cell_style),
            Paragraph(f"{r.duration_mins:.1f}", table_cell_style),
            Paragraph(r.agency or "—", table_cell_style),
            Paragraph(r.equipment or "—", table_cell_style),
            Paragraph(r.description or "—", table_cell_style)
        ])
    if len(log_data) > 1:
        t_logs = Table(log_data, colWidths=[70, 70, 100, 100, 200])
        t_logs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003478')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1DCF0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_logs)
    else:
        story.append(Paragraph("No delay logs logged yet.", body_style))
        
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
