# tpm/utils/calculations.py
import datetime

LOWER_IS_BETTER_KEYWORDS = [
    'breakdown', 'mttr', 'total losses', 'rejection', 'rework',
    'response time', 'repetitive breakdown', 'customer complaint',
    'fatal', 'lti', 'mti', 'near miss', 'accident', 'incident',
    'low illuminated area identified', 'dust level', 'noise level'
]

def compute_achievement(actual: float, target: float, kpi_name: str) -> float:
    """Returns achievement % (can exceed 100 for over-performers)"""
    if actual is None or target is None:
        return 0.0

    lower_is_better = any(
        kw in kpi_name.lower() for kw in LOWER_IS_BETTER_KEYWORDS
    )

    if lower_is_better:
        if target == 0:
            return 100.0 if actual == 0 else 0.0
        return min(100.0, (target / actual) * 100.0) if actual != 0 else 100.0
    else:
        if target == 0:
            return 100.0
        return (actual / target) * 100.0

def compute_PRODUCTION(availability: float, performance: float, quality: float) -> float:
    """PRODUCTION = A x P x Q (inputs as percentages, output as percentage)"""
    if availability is None or performance is None or quality is None:
        return 0.0
    return (availability / 100.0) * (performance / 100.0) * (quality / 100.0) * 100.0

def get_status(achievement: float) -> str:
    """Returns 'on-track' | 'at-risk' | 'behind'"""
    if achievement is None:
        return 'behind'
    if achievement >= 90.0:
        return 'on-track'
    if achievement >= 75.0:
        return 'at-risk'
    return 'behind'

def get_status_css_class(status: str) -> str:
    return {
        'on-track': 'badge-green',
        'at-risk':  'badge-amber',
        'behind':   'badge-red',
    }.get(status, 'badge-muted')

def parse_period(request):
    """
    Parses request.GET parameters and returns a dict with:
      - 'filter_type': 'single' | 'range'
      - 'month': int (for single mode)
      - 'year': int (for single mode)
      - 'from_month': int
      - 'from_year': int
      - 'to_month': int
      - 'to_year': int
      - 'label': string representation of the period (e.g. "Jun 2026" or "Jun 2026 - Dec 2026")
    """
    today = datetime.date.today()
    filter_type = request.GET.get('filter_type', 'single')
    
    if filter_type == 'range':
        # Defaults
        from_month = today.month
        from_year = today.year
        to_month = today.month
        to_year = today.year
        
        from_period_month = request.GET.get('from_period_month')
        if from_period_month and '-' in from_period_month:
            try:
                from_year_str, from_month_str = from_period_month.split('-')
                from_year = int(from_year_str)
                from_month = int(from_month_str)
            except ValueError:
                pass
        else:
            try:
                from_month = int(request.GET.get('from_month', from_month))
                from_year = int(request.GET.get('from_year', from_year))
            except ValueError:
                pass
                
        to_period_month = request.GET.get('to_period_month')
        if to_period_month and '-' in to_period_month:
            try:
                to_year_str, to_month_str = to_period_month.split('-')
                to_year = int(to_year_str)
                to_month = int(to_month_str)
            except ValueError:
                pass
        else:
            try:
                to_month = int(request.GET.get('to_month', to_month))
                to_year = int(request.GET.get('to_year', to_year))
            except ValueError:
                pass
        
        # Ensure start date is not after end date
        if from_year > to_year or (from_year == to_year and from_month > to_month):
            from_month, to_month = to_month, from_month
            from_year, to_year = to_year, from_year
            
        month = from_month
        year = from_year
    else:
        filter_type = 'single'
        month = today.month
        year = today.year
        
        period_month = request.GET.get('period_month')
        if period_month and '-' in period_month:
            try:
                year_str, month_str = period_month.split('-')
                year = int(year_str)
                month = int(month_str)
            except ValueError:
                pass
        else:
            try:
                month = int(request.GET.get('month', month))
                year = int(request.GET.get('year', year))
            except ValueError:
                pass
                
        from_month = to_month = month
        from_year = to_year = year
        
    months_map = dict([
        (1, 'Jan'), (2, 'Feb'), (3, 'Mar'), (4, 'Apr'),
        (5, 'May'), (6, 'Jun'), (7, 'Jul'), (8, 'Aug'),
        (9, 'Sep'), (10, 'Oct'), (11, 'Nov'), (12, 'Dec')
    ])
    
    if filter_type == 'single':
        months_full = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        label = f"{dict(months_full).get(month)} {year}"
    else:
        label = f"{months_map.get(from_month)} {from_year} - {months_map.get(to_month)} {to_year}"
        
    return {
        'filter_type': filter_type,
        'month': month,
        'year': year,
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'label': label,
    }

def get_date_range_q(prefix='', from_month=1, from_year=2025, to_month=12, to_year=2026):
    from django.db.models import Q
    month_field = f"{prefix}month"
    year_field = f"{prefix}year"
    
    if from_year == to_year:
        return Q(**{f"{year_field}": from_year, f"{month_field}__gte": from_month, f"{month_field}__lte": to_month})
    
    q_start = Q(**{f"{year_field}": from_year, f"{month_field}__gte": from_month})
    q_middle = Q(**{f"{year_field}__gt": from_year, f"{year_field}__lt": to_year})
    q_end = Q(**{f"{year_field}": to_year, f"{month_field}__lte": to_month})
    
    return q_start | q_middle | q_end

def aggregate_kpi_actual(kpi_values_queryset, uom, kpi_name):
    """
    Given a queryset of KPIValue objects, return the aggregated actual,
    aggregated target, and aggregated benchmark.
    """
    from django.db.models import Avg, Sum
    
    if not kpi_values_queryset.exists():
        return None, None, None
        
    lower_name = kpi_name.lower()
    lower_uom = uom.lower()
    
    # Check if we should sum or average
    is_average = (
        '%' in lower_uom or 
        'score' in lower_uom or 
        'db' in lower_uom or 
        'ug/m3' in lower_uom or 
        'mg/m3' in lower_uom or
        'man hrs/emp' in lower_uom or
        'ton/man' in lower_name or
        'PRODUCTION' in lower_name or
        'mtbf' in lower_name or
        'mttr' in lower_name or
        'productivity' in lower_name
    )
    
    if is_average:
        agg_actual = kpi_values_queryset.aggregate(val=Avg('actual'))['val']
        agg_target = kpi_values_queryset.aggregate(val=Avg('target'))['val']
        agg_benchmark = kpi_values_queryset.aggregate(val=Avg('benchmark'))['val']
    else:
        agg_actual = kpi_values_queryset.aggregate(val=Sum('actual'))['val']
        # If target/benchmark are percentages or rates, average them; otherwise sum them
        if '%' in lower_uom or 'score' in lower_uom or 'db' in lower_uom or 'ug/m3' in lower_uom or 'mg/m3' in lower_uom or 'man hrs/emp' in lower_uom:
            agg_target = kpi_values_queryset.aggregate(val=Avg('target'))['val']
            agg_benchmark = kpi_values_queryset.aggregate(val=Avg('benchmark'))['val']
        else:
            agg_target = kpi_values_queryset.aggregate(val=Sum('target'))['val']
            agg_benchmark = kpi_values_queryset.aggregate(val=Sum('benchmark'))['val']
            
    return (
        round(agg_actual, 2) if agg_actual is not None else None,
        round(agg_target, 2) if agg_target is not None else None,
        round(agg_benchmark, 2) if agg_benchmark is not None else None
    )

def aggregate_ws_actual(ws_values_queryset, uom, kpi_name):
    from django.db.models import Avg, Sum
    
    if not ws_values_queryset.exists():
        return None
        
    lower_name = kpi_name.lower()
    lower_uom = uom.lower()
    
    is_average = (
        '%' in lower_uom or 
        'score' in lower_uom or 
        'db' in lower_uom or 
        'ug/m3' in lower_uom or 
        'mg/m3' in lower_uom or
        'man hrs/emp' in lower_uom or
        'ton/man' in lower_name or
        'PRODUCTION' in lower_name or
        'mtbf' in lower_name or
        'mttr' in lower_name or
        'productivity' in lower_name
    )
    
    if is_average:
        val = ws_values_queryset.aggregate(val=Avg('actual'))['val']
    else:
        val = ws_values_queryset.aggregate(val=Sum('actual'))['val']
        
    return round(val, 2) if val is not None else None


def get_jh_kaizen_count(dept, month, year):
    from tpm.models import KaizenSheet
    sheets = KaizenSheet.objects.filter(department=dept, pillar='JH')
    count = 0
    for sheet in sheets:
        if sheet.finish_date:
            for fmt in ('%d-%m-%Y', '%Y-%m-%d'):
                try:
                    dt = datetime.datetime.strptime(sheet.finish_date.strip(), fmt)
                    if dt.month == month and dt.year == year:
                        count += 1
                        break
                except ValueError:
                    pass
    return count


def get_jh_kaizen_count_range(dept, from_month, from_year, to_month, to_year):
    from tpm.models import KaizenSheet
    sheets = KaizenSheet.objects.filter(department=dept, pillar='JH')
    count = 0
    start = from_year * 12 + from_month
    end = to_year * 12 + to_month
    for sheet in sheets:
        if sheet.finish_date:
            for fmt in ('%d-%m-%Y', '%Y-%m-%d'):
                try:
                    dt = datetime.datetime.strptime(sheet.finish_date.strip(), fmt)
                    current = dt.year * 12 + dt.month
                    if start <= current <= end:
                        count += 1
                        break
                except ValueError:
                    pass
    return count


def update_jh_kaizen_kpi_value(dept, month, year):
    from tpm.models import PillarEntry, KPIValue
    from tpm.utils.kpi_definitions import KPI_DEFINITIONS
    
    # Calculate count
    count = get_jh_kaizen_count(dept, month, year)
    
    # Get or create PillarEntry for JH in this month/year
    entry, created = PillarEntry.objects.get_or_create(
        department=dept, pillar='JH', month=month, year=year
    )
    
    # Get JH row 6 definition
    jh_defs = KPI_DEFINITIONS.get('JH', [])
    kpi_meta = next((d for d in jh_defs if d['sl_no'] == '6'), None)
    if kpi_meta:
        db_val, created_val = KPIValue.objects.get_or_create(
            pillar_entry=entry, sl_no='6',
            defaults={
                'kpi_name': kpi_meta['name'],
                'uom': kpi_meta['uom'],
                'benchmark': kpi_meta['benchmark'],
                'target': kpi_meta['target'],
                'actual': count
            }
        )
        if not created_val and db_val.actual != count:
            db_val.actual = count
            db_val.save(update_fields=['actual'])


