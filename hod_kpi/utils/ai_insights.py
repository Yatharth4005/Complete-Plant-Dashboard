import os
import json
import urllib.request
import urllib.error
from hod_kpi.models import HODKPIUpload, HODKPIRecord, HODKPIDelayRecord

def generate_insights_from_data(upload_obj):
    """
    Generates AI performance insights and recommendations for the HOD KPI upload.
    Utilizes Gemini API if API key is present in environment, otherwise falls back
    to a robust rule-based logic generator.
    """
    records = upload_obj.records.all()
    delays = upload_obj.delays.all()
    
    # 1. Gather data for prompt/rules
    summary_data = {
        "department": upload_obj.department.name,
        "period": f"{upload_obj.month:02d}/{upload_obj.year}",
        "reporting_date": str(upload_obj.reporting_date),
        "total_kpis": records.count(),
        "green_kpis": records.filter(status='GREEN').count(),
        "yellow_kpis": records.filter(status='YELLOW').count(),
        "red_kpis": records.filter(status='RED').count(),
        "below_target": [],
        "met_target": [],
        "delays": []
    }
    
    for r in records:
        info = {
            "name": r.kpi_name,
            "domain": r.domain,
            "view": r.view_type,
            "actual": r.actual,
            "target": r.target,
            "achievement": r.achievement_pct,
            "status": r.status
        }
        if r.status in ['RED', 'YELLOW']:
            summary_data["below_target"].append(info)
        else:
            summary_data["met_target"].append(info)
            
    for d in delays[:5]: # Take top 5 delays
        summary_data["delays"].append({
            "reason": d.reason,
            "cause": d.department_cause,
            "duration": d.duration_mins,
            "percentage": d.contribution_pct
        })
        
    # Check if Gemini API key exists
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            return call_gemini_api(summary_data, api_key)
        except Exception as e:
            # Fallback on failure
            return generate_rule_based_insights(summary_data, error=str(e))
    else:
        return generate_rule_based_insights(summary_data)

def call_gemini_api(data, api_key):
    """
    Calls Google Gemini API to get intelligent performance insights.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    You are an expert industrial engineering AI consultant specialized in steel plant operations management (Plate Mill).
    Analyze the following monthly performance data and generate:
    1. A professional, detailed summary (2-3 paragraphs) assessing achievements and core pain points.
    2. A list of 4-5 highly actionable, structured recommendations (as a JSON array of strings).

    Performance Data:
    Department: {data['department']}
    Period: {data['period']}
    Total KPIs: {data['total_kpis']} (Green: {data['green_kpis']}, Yellow: {data['yellow_kpis']}, Red: {data['red_kpis']})
    
    KPIs Below Target:
    {json.dumps(data['below_target'], indent=2)}
    
    KPIs Meeting Target:
    {json.dumps(data['met_target'], indent=2)}
    
    Top Delays / Downtime Reasons:
    {json.dumps(data['delays'], indent=2)}

    Your output MUST be in valid JSON format with the following keys:
    - "summary": (string) paragraph of analysis
    - "recommendations": (list of strings) actionable steps
    Do not output any markdown wrapping or text outside the JSON object.
    """
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    data_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            # Clean possible markdown formatting
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            parsed = json.loads(text.strip())
            return parsed.get("summary", ""), parsed.get("recommendations", [])
    except urllib.error.URLError as e:
        raise Exception(f"Gemini API request failed: {e}")

def generate_rule_based_insights(data, error=None):
    """
    Generates rule-based insights if AI API is not available or fails.
    """
    dept = data["department"]
    period = data["period"]
    
    # 1. Construct Summary
    total = data["total_kpis"]
    green = data["green_kpis"]
    red = data["red_kpis"]
    yellow = data["yellow_kpis"]
    
    compliance = round((green / total) * 100.0, 1) if total > 0 else 100.0
    
    summary = f"During the reporting period {period}, the {dept} demonstrated a KPI compliance rate of {compliance}% (meeting target in {green} out of {total} tracked metrics). "
    
    # Analyze production
    prod_below = [k for k in data["below_target"] if k["domain"] == 'PRODUCTION']
    prod_ok = [k for k in data["met_target"] if k["domain"] == 'PRODUCTION']
    
    if prod_below:
        summary += f"Production output faced headwinds, with key areas like {', '.join([k['name'] for k in prod_below])} falling short of targets. "
    elif prod_ok:
        summary += "Production KPIs remained stable, meeting the monthly operating targets across all major product lines. "
        
    # Analyze quality
    qual_below = [k for k in data["below_target"] if k["domain"] == 'QUALITY']
    if qual_below:
        summary += f"Quality metrics require attention as {', '.join([k['name'] for k in qual_below])} fell below benchmarks, indicating opportunities for process stabilization. "
    else:
        summary += "Quality parameters showed excellent compliance, indicating stable process control and high First Time Right (FTR) yields. "
        
    # Analyze delays
    if data["delays"]:
        top_delay = data["delays"][0]
        summary += f"Downtime analysis highlights that '{top_delay['reason']}' was the primary contributor, accounting for {top_delay['duration']} minutes ({top_delay['percentage']}% of total delays), primarily attributed to the {top_delay['cause']} agency."
        
    if error:
        summary += f" (Note: AI engine was unavailable. Falling back to rule-based insights generator.)"

    # 2. Construct Recommendations
    recommendations = []
    
    # Dynamic recommendations based on data
    # Prod recommendations
    for k in prod_below:
        recommendations.append(f"Deploy standard operating procedures (SOP) revisions and review shift utilization plans to recover the {k['name']} deficit (current: {k['actual']}{k['uom']} vs target: {k['target']}{k['uom']}).")
        
    # Quality recommendations
    for k in qual_below:
        recommendations.append(f"Execute daily heat/slab tracking reviews to identify root causes for below-target {k['name']} (achievement: {k['achievement']}%). Check slabbing/re-heating thermal profiles.")
        
    # Cost recommendations
    cost_below = [k for k in data["below_target"] if k["domain"] == 'COST']
    for k in cost_below:
        recommendations.append(f"Optimize fuel-air ratio controls and power management sequences to reduce {k['name']} variance (actual is higher than target: {k['actual']}{k['uom']} vs target: {k['target']}{k['uom']}).")
        
    # Delay recommendations
    if data["delays"]:
        top_delay = data["delays"][0]
        recommendations.append(f"Coordinate a cross-functional breakdown audit with the {top_delay['cause']} department regarding '{top_delay['reason']}' to minimize recurrent delays.")
        
    # General fallbacks if recommendations list is short
    if len(recommendations) < 3:
        recommendations.append("Enhance preventive maintenance checklists for secondary rolling and descaling equipment during planned shutdowns.")
    if len(recommendations) < 4:
        recommendations.append("Strengthen daily safety observation closure speed to ensure compliance with site hazard reporting protocols.")
    if len(recommendations) < 5:
        recommendations.append("Implement weekly review cycles for operator training logs on the finishing and shearing lines.")
        
    return summary, recommendations
