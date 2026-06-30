import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count
from tpm.models import Department, User
from .models import HODKPIUpload, HODKPIRecord, HODKPIDelayRecord, HODKPIMonthlySubmission
from .utils.parser import parse_hod_kpi_excel, save_parsed_data
from .utils.ai_insights import generate_insights_from_data
from portal.models import PortalNotification, Module

# Month name mapping helper
MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
    7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

@login_required
def hod_kpi_dashboard(request):
    dept_id = request.GET.get('department_id')
    if not dept_id and request.user.department:
        dept_id = request.user.department.id
    if not dept_id:
        dept = Department.objects.first()
    else:
        dept = get_object_or_404(Department, id=dept_id)
        
    if not dept:
        return HttpResponse("No department configured in the system.", status=404)

    # Month and Year selection
    now = timezone.now()
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    month = int(month) if month else now.month
    year = int(year) if year else now.year

    # Try to find upload and submission
    upload = HODKPIUpload.objects.filter(department=dept, month=month, year=year).first()
    submission = HODKPIMonthlySubmission.objects.filter(department=dept, month=month, year=year).first()

    context = {
        'department': dept,
        'active_dept_id': dept.id,
        'active_module': 'HOD_KPI',
        'month': month,
        'year': year,
        'month_name': MONTH_NAMES.get(month, ''),
        'upload': upload,
        'submission': submission,
    }

    if upload:
        context['upload_filename'] = upload.file.name.split('/')[-1]
        
        # Pull KPI Records grouped by domain
        records = upload.records.all()
        context['production_mtd'] = records.filter(domain='PRODUCTION', view_type='MTD')
        context['production_ytd'] = records.filter(domain='PRODUCTION', view_type='YTD')
        context['production_wtd'] = records.filter(domain='PRODUCTION', view_type='WTD')
        context['quality_records'] = records.filter(domain='QUALITY')
        context['oee_records'] = records.filter(domain='OEE')
        context['safety_records'] = records.filter(domain='SAFETY')
        context['cost_records'] = records.filter(domain='COST')
        
        # Below target records
        context['below_target_records'] = records.filter(is_below_target=True)
        
        # Compliance calculations
        total_kpis = records.count()
        green_kpis = records.filter(status='GREEN').count()
        context['compliance_pct'] = round((green_kpis / total_kpis) * 100.0, 1) if total_kpis > 0 else 100.0
        context['green_count'] = green_kpis
        context['yellow_count'] = records.filter(status='YELLOW').count()
        context['red_count'] = records.filter(status='RED').count()
        
        # Safety LTI indicator for alert banner
        lti_rec = records.filter(domain='SAFETY', kpi_name__iexact='LTI').first()
        context['lti_actual'] = lti_rec.actual if lti_rec else 0
        
        # Delay records
        context['delay_records'] = upload.delays.all()
        
        # AI Recommendations list decode
        if submission and submission.ai_recommendations:
            try:
                context['ai_recommendations_list'] = json.loads(submission.ai_recommendations)
            except Exception:
                context['ai_recommendations_list'] = []

    return render(request, 'hod_kpi/dashboard.html', context)


@login_required
def upload_excel(request):
    if request.method == 'POST':
        month = request.POST.get('month')
        year = request.POST.get('year')
        dept_id = request.POST.get('department_id')
        excel_file = request.FILES.get('excel_file')
        
        if not excel_file:
            messages.error(request, "Please select an Excel file to upload.")
            return redirect(f"/hod-kpi/dashboard/?department_id={dept_id}&month={month}&year={year}")
            
        dept = get_object_or_404(Department, id=dept_id)
        
        # Save temporary file for parsing
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'hod_kpi', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, excel_file.name)
        
        with open(temp_path, 'wb+') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)
                
        try:
            # Parse Excel File
            parsed_data = parse_hod_kpi_excel(temp_path, filename=excel_file.name)
            
            # If the parser finds different month/year from Excel, trust the Excel/parser
            p_month = parsed_data["upload_meta"]["month"] or int(month)
            p_year = parsed_data["upload_meta"]["year"] or int(year)
            
            # Save Parsed data to models
            upload_obj, submission_obj = save_parsed_data(
                parsed_data, 
                excel_file, 
                dept.id, 
                request.user
            )
            
            messages.success(request, f"Excel report parsed successfully for {MONTH_NAMES.get(p_month)} {p_year}!")
            return redirect(f"/hod-kpi/dashboard/?department_id={dept.id}&month={p_month}&year={p_year}")
            
        except Exception as e:
            messages.error(request, f"Parser Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return redirect(f"/hod-kpi/dashboard/?department_id={dept_id}&month={month}&year={year}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return redirect("/hod-kpi/dashboard/")


@login_required
def save_kpi_feedback(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            record_id = body.get('record_id')
            field = body.get('field')
            value = body.get('value')
            
            record = get_object_or_404(HODKPIRecord, id=record_id)
            
            # Security / Submission check
            submission = HODKPIMonthlySubmission.objects.filter(
                department=record.upload.department,
                month=record.upload.month,
                year=record.upload.year
            ).first()
            
            if submission and submission.status == 'SUBMITTED':
                return JsonResponse({"status": "error", "message": "Review already submitted & locked."}, status=403)

            # Map inputs to fields
            if field == 'reason_deviation':
                record.reason_deviation = value
            elif field == 'root_cause':
                record.root_cause = value
            elif field == 'corrective_action':
                record.corrective_action = value
            elif field == 'responsible_owner':
                record.responsible_owner = value
            elif field == 'completion_date':
                record.completion_date = value if value else None
            elif field == 'remarks':
                record.remarks = value
            else:
                return JsonResponse({"status": "error", "message": "Invalid field specification."}, status=400)
                
            record.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@login_required
def save_delay_explanation(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            delay_id = body.get('delay_id')
            explanation = body.get('explanation')
            
            delay = get_object_or_404(HODKPIDelayRecord, id=delay_id)
            
            submission = HODKPIMonthlySubmission.objects.filter(
                department=delay.upload.department,
                month=delay.upload.month,
                year=delay.upload.year
            ).first()
            
            if submission and submission.status == 'SUBMITTED':
                return JsonResponse({"status": "error", "message": "Locked."}, status=403)
                
            delay.explanation = explanation
            delay.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@login_required
def save_monthly_inputs(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            sub_id = body.get('submission_id')
            field = body.get('field')
            value = body.get('value')
            
            sub = get_object_or_404(HODKPIMonthlySubmission, id=sub_id)
            
            if sub.status == 'SUBMITTED':
                return JsonResponse({"status": "error", "message": "Locked."}, status=403)
                
            if field == 'achievements':
                sub.achievements = value
            elif field == 'risks':
                sub.risks = value
            elif field == 'support_required':
                sub.support_required = value
            elif field == 'resources_required':
                sub.resources_required = value
            elif field == 'special_observations':
                sub.special_observations = value
            else:
                return JsonResponse({"status": "error", "message": "Invalid field."}, status=400)
                
            sub.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@login_required
def generate_ai_insights(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            sub_id = body.get('submission_id')
            sub = get_object_or_404(HODKPIMonthlySubmission, id=sub_id)
            
            if sub.status == 'SUBMITTED':
                return JsonResponse({"status": "error", "message": "Review already submitted."}, status=403)
                
            # Call AI insights generator
            summary, recommendations = generate_insights_from_data(sub.upload)
            
            # Save to submission object
            sub.ai_summary = summary
            sub.ai_recommendations = json.dumps(recommendations)
            sub.save()
            
            return JsonResponse({
                "status": "success",
                "summary": summary,
                "recommendations": recommendations
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@login_required
def submit_review(request):
    if request.method == 'POST':
        sub_id = request.POST.get('submission_id')
        sub = get_object_or_404(HODKPIMonthlySubmission, id=sub_id)
        
        # Verify deviation entries are filled for below-target metrics
        below_target_recs = sub.upload.records.filter(is_below_target=True)
        missing_capa = False
        for r in below_target_recs:
            if not r.reason_deviation or not r.root_cause or not r.corrective_action:
                missing_capa = True
                break
                
        if missing_capa:
            messages.error(request, "Cannot submit review: Please fill in the Reason, Root Cause, and CAPA fields for all below-target KPIs.")
            return redirect(f"/hod-kpi/dashboard/?department_id={sub.department.id}&month={sub.month}&year={sub.year}")
            
        sub.status = 'SUBMITTED'
        sub.submitted_at = timezone.now()
        sub.submitted_by = request.user
        sub.save()
        
        # Create notification for admins
        admins = User.objects.filter(is_plant_admin=True)
        for admin in admins:
            PortalNotification.objects.create(
                user=admin,
                message=f"📊 HOD KPI Review for {sub.department.name} ({MONTH_NAMES.get(sub.month)} {sub.year}) has been submitted by {request.user.get_display_name()}.",
                link=f"/hod-kpi/dashboard/?department_id={sub.department.id}&month={sub.month}&year={sub.year}"
            )
            
        messages.success(request, f"HOD KPI Review for {sub.department.name} successfully submitted and locked!")
        return redirect(f"/hod-kpi/dashboard/?department_id={sub.department.id}&month={sub.month}&year={sub.year}")
        
    return redirect("/hod-kpi/dashboard/")


@login_required
def review_history(request):
    dept_id = request.GET.get('department_id')
    if not dept_id and request.user.department:
        dept_id = request.user.department.id
    if not dept_id:
        dept = Department.objects.first()
    else:
        dept = get_object_or_404(Department, id=dept_id)
        
    submissions = HODKPIMonthlySubmission.objects.filter(department=dept).order_by('-year', '-month')
    
    # We can present list of historical reviews
    # Let's just redirect to dashboard or make a simple template
    # For now, let's redirect to dashboard of the latest submission
    latest = submissions.first()
    if latest:
        return redirect(f"/hod-kpi/dashboard/?department_id={dept.id}&month={latest.month}&year={latest.year}")
    
    return redirect(f"/hod-kpi/dashboard/?department_id={dept.id}")
