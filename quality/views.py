import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Avg, Count
from django.contrib import messages
from django.utils import timezone
from tpm.models import Department
from quality.models import QualityEntry, NonFTRReason

def quality_dashboard(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    # Calculate current Month-to-Date (MTD) dates
    today = timezone.localtime(timezone.now()).date()
    start_of_month = today.replace(day=1)
    
    # MTD Entries for active department
    mtd_entries = QualityEntry.objects.filter(
        department=department,
        date__range=[start_of_month, today]
    )
    
    # Summary Metrics
    total_inspections = mtd_entries.aggregate(val=Sum('inspected_qty'))['val'] or 0.0
    rework_tonnage = mtd_entries.aggregate(val=Sum('rework_qty'))['val'] or 0.0
    total_entries = mtd_entries.count()
    pending_reviews = QualityEntry.objects.filter(department=department, status='DRAFT').count()
    
    sum_ftr = mtd_entries.aggregate(val=Sum('ftr_qty'))['val'] or 0.0
    mtd_ftr_percent = (sum_ftr / total_inspections * 100) if total_inspections > 0 else 100.0
    
    # 1. Doughnut Distribution (MTD)
    dist_95_count = mtd_entries.filter(ftr_percent__gte=95.0).count()
    dist_90_95_count = mtd_entries.filter(ftr_percent__gte=90.0, ftr_percent__lt=95.0).count()
    dist_less_90_count = mtd_entries.filter(ftr_percent__lt=90.0).count()
    
    # 2. FTR % by Section (Product Type)
    section_stats = mtd_entries.values('product_type').annotate(
        avg_ftr=Avg('ftr_percent')
    ).exclude(product_type__isnull=True).exclude(product_type='')
    
    section_labels = [s['product_type'] for s in section_stats]
    section_data = [round(s['avg_ftr'], 2) for s in section_stats]
    
    # 3. FTR Performance by Shift
    shift_perf = []
    for s_code in ['A', 'B', 'C']:
        shift_entries = mtd_entries.filter(shift=s_code)
        s_inspected = shift_entries.aggregate(val=Sum('inspected_qty'))['val'] or 0.0
        s_ftr = shift_entries.aggregate(val=Sum('ftr_qty'))['val'] or 0.0
        s_percent = (s_ftr / s_inspected * 100) if s_inspected > 0 else 100.0
        shift_perf.append({
            'shift': s_code,
            'inspected': s_inspected,
            'ftr': s_ftr,
            'percent': s_percent
        })
        
    # 4. Top Non-FTR Reasons
    top_reasons_qs = NonFTRReason.objects.filter(
        quality_entry__department=department,
        quality_entry__date__range=[start_of_month, today]
    ).values('reason').annotate(
        total_qty=Sum('qty')
    ).order_by('-total_qty')[:5]
    
    total_reason_qty = sum(r['total_qty'] for r in top_reasons_qs) or 1.0
    top_non_ftr = []
    for r in top_reasons_qs:
        top_non_ftr.append({
            'reason': r['reason'],
            'total_qty': r['total_qty'],
            'percent': (r['total_qty'] / total_reason_qty * 100)
        })
        
    # 5. Trend Chart Generation (Last 7 Days)
    trend_labels = []
    trend_daily_data = []
    trend_mtd_data = []
    
    for i in range(6, -1, -1):
        day_date = today - datetime.timedelta(days=i)
        trend_labels.append(day_date.strftime('%d-%b'))
        
        # Daily FTR
        day_entries = QualityEntry.objects.filter(department=department, date=day_date)
        d_inspected = day_entries.aggregate(val=Sum('inspected_qty'))['val'] or 0.0
        d_ftr = day_entries.aggregate(val=Sum('ftr_qty'))['val'] or 0.0
        d_pct = (d_ftr / d_inspected * 100) if d_inspected > 0 else 100.0
        trend_daily_data.append(round(d_pct, 2))
        
        # Cumulative MTD FTR to that date
        mtd_to_date_entries = QualityEntry.objects.filter(
            department=department, 
            date__range=[start_of_month, day_date]
        )
        cum_inspected = mtd_to_date_entries.aggregate(val=Sum('inspected_qty'))['val'] or 0.0
        cum_ftr = mtd_to_date_entries.aggregate(val=Sum('ftr_qty'))['val'] or 0.0
        cum_pct = (cum_ftr / cum_inspected * 100) if cum_inspected > 0 else 100.0
        trend_mtd_data.append(round(cum_pct, 2))
        
    # Recent Entries
    recent_entries = QualityEntry.objects.filter(department=department).order_by('-date', '-created_at')[:10]
    
    context = {
        'department': department,
        'active_tab': 'dashboard',
        'total_inspections': total_inspections,
        'rework_tonnage': rework_tonnage,
        'total_entries': total_entries,
        'pending_reviews': pending_reviews,
        'mtd_ftr_percent': mtd_ftr_percent,
        'dist_95_count': dist_95_count,
        'dist_90_95_count': dist_90_95_count,
        'dist_less_90_count': dist_less_90_count,
        'section_labels': section_labels,
        'section_data': section_data,
        'shift_perf': shift_perf,
        'top_non_ftr': top_non_ftr,
        'trend_labels': trend_labels,
        'trend_daily_data': trend_daily_data,
        'trend_mtd_data': trend_mtd_data,
        'recent_entries': recent_entries,
    }
    return render(request, 'quality/dashboard.html', context)

def quality_entry(request, dept_id, entry_id=None):
    department = get_object_or_404(Department, id=dept_id)
    entry = None
    if entry_id:
        entry = get_object_or_404(QualityEntry, id=entry_id, department=department)
        entry_no = entry.entry_no
    else:
        # Generate next entry number
        count = QualityEntry.objects.count() + 1
        entry_no = f"Q-{count:06d}"
        
    if request.method == 'POST':
        # Get POST details
        date_str = request.POST.get('date')
        shift = request.POST.get('shift') or 'A'
        action = request.POST.get('action') # 'draft' or 'submit'
        
        status = QualityEntry.STATUS_SUBMITTED if action == 'submit' else QualityEntry.STATUS_DRAFT
        
        inspected_qty = float(request.POST.get('inspected_qty') or 0.0)
        ftr_qty = float(request.POST.get('ftr_qty') or 0.0)
        accepted_qty = float(request.POST.get('accepted_qty') or 0.0)
        
        ftr_pct = (ftr_qty / inspected_qty * 100.0) if inspected_qty > 0 else 100.0
        
        if not entry:
            entry = QualityEntry(
                department=department,
                entry_no=entry_no,
                created_by=request.user
            )
            
        entry.date = date_str
        entry.shift = shift
        entry.status = status
        
        # Heat & Product Details
        entry.caster_type = request.POST.get('caster_type')
        entry.product_type = request.POST.get('product')
        entry.section_type = request.POST.get('section_type')
        entry.grade = request.POST.get('grade')
        entry.heat_number = request.POST.get('heat_number')
        entry.inspected_qty = inspected_qty
        entry.ftr_qty = ftr_qty
        
        # Defect Details
        entry.defect_type = request.POST.get('defect_type')
        entry.defect_category = request.POST.get('defect_category')
        entry.defect_severity = request.POST.get('defect_severity')
        entry.defect_qty = float(request.POST.get('defect_qty') or 0.0)
        entry.rejected_qty = float(request.POST.get('rejected_qty') or 0.0)
        entry.reason_of_defect = request.POST.get('reason_of_defect')
        
        # Rework Details
        entry.rework_type = request.POST.get('rework_type')
        entry.rework_qty = float(request.POST.get('rework_qty') or 0.0)
        entry.reason_for_rework = request.POST.get('reason_for_rework')
        
        # Diversion Details
        entry.diversion_type = request.POST.get('diversion_type')
        entry.diversion_qty = float(request.POST.get('diversion_qty') or 0.0)
        entry.reason_for_diversion = request.POST.get('reason_for_diversion')
        
        # Mix Grade Details
        entry.mix_grade = request.POST.get('mix_grade')
        entry.mix_qty = float(request.POST.get('mix_qty') or 0.0)
        entry.reason_for_mix_grade = request.POST.get('reason_for_mix_grade')
        
        # POR Details
        entry.por_type = request.POST.get('por_type')
        entry.por_qty = float(request.POST.get('por_qty') or 0.0)
        entry.por_doc_ref = request.POST.get('por_doc_ref')
        entry.por_remarks = request.POST.get('por_remarks')
        
        # FTR Details
        entry.accepted_qty = accepted_qty
        entry.ftr_percent = ftr_pct
        entry.inspection_status = request.POST.get('inspection_status')
        
        # PSFS Details
        entry.psfs_type = request.POST.get('psfs_type')
        entry.psfs_qty = float(request.POST.get('psfs_qty') or 0.0)
        entry.reason_for_psfs = request.POST.get('reason_for_psfs')
        
        entry.remarks = request.POST.get('remarks')
        
        if 'attachment' in request.FILES:
            entry.attachment = request.FILES['attachment']
            
        entry.save()
        
        # Save dynamic Non-FTR reasons
        entry.non_ftr_reasons.all().delete()
        reasons_list = request.POST.getlist('non_ftr_reason[]')
        qtys_list = request.POST.getlist('non_ftr_qty[]')
        
        for r_name, r_qty in zip(reasons_list, qtys_list):
            if r_name and r_qty:
                NonFTRReason.objects.create(
                    quality_entry=entry,
                    reason=r_name,
                    qty=float(r_qty)
                )
                
        messages.success(request, f"Quality entry {entry_no} saved successfully as {status}.")
        return redirect('quality:quality_dashboard', dept_id=department.id)
        
    today_str = timezone.localtime(timezone.now()).date().strftime('%Y-%m-%d')
    context = {
        'department': department,
        'active_tab': 'entry',
        'entry': entry,
        'entry_no': entry_no,
        'today_str': today_str,
    }
    return render(request, 'quality/quality_entry.html', context)

def delete_quality_entry(request, dept_id, entry_id):
    department = get_object_or_404(Department, id=dept_id)
    entry = get_object_or_404(QualityEntry, id=entry_id, department=department)
    entry_no = entry.entry_no
    entry.delete()
    messages.success(request, f"Quality log {entry_no} deleted successfully.")
    return redirect('quality:quality_dashboard', dept_id=department.id)

def quality_summary_report(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    # Filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    caster_type = request.GET.get('caster_type')
    product_type = request.GET.get('product_type')
    search_query = request.GET.get('q')
    
    entries = QualityEntry.objects.filter(department=department).order_by('-date', '-created_at')
    
    if start_date:
        entries = entries.filter(date__gte=start_date)
    if end_date:
        entries = entries.filter(date__lte=end_date)
    if caster_type:
        entries = entries.filter(caster_type=caster_type)
    if product_type:
        entries = entries.filter(product_type=product_type)
    if search_query:
        from django.db.models import Q
        entries = entries.filter(
            Q(entry_no__icontains=search_query) |
            Q(heat_number__icontains=search_query) |
            Q(grade__icontains=search_query) |
            Q(defect_type__icontains=search_query) |
            Q(product_type__icontains=search_query)
        )
        
    # Get distinct options for filter dropdowns
    casters = QualityEntry.objects.filter(department=department).values_list('caster_type', flat=True).distinct()
    casters = sorted([c for c in casters if c])
    
    products = QualityEntry.objects.filter(department=department).values_list('product_type', flat=True).distinct()
    products = sorted([p for p in products if p])
    
    context = {
        'department': department,
        'active_tab': 'summary_report',
        'entries': entries,
        'casters': casters,
        'products': products,
        'start_date': start_date,
        'end_date': end_date,
        'caster_type': caster_type,
        'product_type': product_type,
        'q': search_query,
    }
    return render(request, 'quality/summary_report.html', context)
