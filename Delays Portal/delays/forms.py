from django import forms
from tpm.models import Department
from delays.models import DelayRecord, DelayDropdownOption
from delays.utils.parser import normalize_agency_name

class DelayRecordForm(forms.ModelForm):
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'input-mono', 'id': 'id_end_date'})
    )
    agency_type = forms.ChoiceField(
        choices=[('Internal', 'Internal'), ('External', 'External')],
        required=True,
        widget=forms.Select(attrs={'class': 'input-mono', 'id': 'id_agency_type'})
    )
    agency = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'input-mono', 'id': 'id_agency'}))
    sub_agency = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    sub_area = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    equipment = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    sub_equipment = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    shift_incharge = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    action = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-mono', 'rows': 2, 'placeholder': 'Action taken to resolve the delay'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-mono', 'rows': 3, 'placeholder': 'Detailed description of the delay/breakdown'}))
    duration_mins = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'input-mono',
            'id': 'id_duration_mins',
            'step': 'any',
            'placeholder': 'Duration in minutes'
        })
    )
    production_loss = forms.FloatField(
        required=False,
        initial=0.0,
        widget=forms.NumberInput(attrs={
            'class': 'input-mono',
            'placeholder': 'Production loss in tons',
            'step': 'any'
        })
    )
    has_production_loss = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'id': 'id_has_production_loss',
            'style': 'cursor: pointer; transform: scale(1.2); margin-right: 8px;'
        })
    )

    class Meta:
        model = DelayRecord
        fields = [
            'date', 'end_date', 'start_time', 'end_time', 'duration_mins', 'has_production_loss', 'production_loss',
            'agency_type', 'agency', 'sub_agency', 'sub_area', 'equipment', 'sub_equipment',
            'shift_incharge', 'description', 'action'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono', 'id': 'id_date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'input-mono', 'id': 'id_start_time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'input-mono', 'id': 'id_end_time'}),
        }

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        if not self.initial.get('end_date') and self.initial.get('date'):
            self.initial['end_date'] = self.initial.get('date')
        
        # Default choices if nothing in DB
        agency_list = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
        equip_list = []
        sub_agency_list = []
        sub_equip_list = []
        incharge_list = []
        
        if department:
            # Fetch custom agencies from dropdown options and normalize them to deduplicate
            raw_agencies = DelayDropdownOption.objects.filter(
                department=department, category__iexact='Agency'
            ).values_list('value', flat=True).distinct()
            agency_list = sorted(list(set(normalize_agency_name(a) for a in raw_agencies if a)))
            if not agency_list:
                agency_list = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']

            # Fetch custom equipments from dropdown options with their categories (parent_value)
            equip_opts = DelayDropdownOption.objects.filter(
                department=department, category__iexact='Equipment'
            )
            equip_list = []
            for opt in equip_opts:
                display_name = f"{opt.value} ({opt.parent_value})" if opt.parent_value else opt.value
                equip_list.append((opt.value, display_name))
            
            equip_list.sort(key=lambda x: x[0])
                
            # Fetch sub-agencies from dropdown options
            sub_agencies_set = set(DelayDropdownOption.objects.filter(
                department=department, category__iexact='Sub-Agency'
            ).values_list('value', flat=True).distinct())
            sub_agency_list = sorted([x for x in sub_agencies_set if x])

            # Fetch sub-areas from dropdown options
            sub_areas_set = set(DelayDropdownOption.objects.filter(
                department=department, category__iexact='Sub-Area'
            ).values_list('value', flat=True).distinct())
            sub_area_list = sorted([x for x in sub_areas_set if x])

            # Fetch sub-equipments from dropdown options only
            sub_equip_set = set(DelayDropdownOption.objects.filter(
                department=department, category__iexact='Sub-Equipment'
            ).values_list('value', flat=True).distinct())
            sub_equip_list = sorted([x for x in sub_equip_set if x])

            # Fetch shift incharges from dropdown options
            incharge_opts = DelayDropdownOption.objects.filter(
                department=department, category__iexact='Shift Incharge'
            )
            incharge_list = []
            for opt in incharge_opts:
                if opt.parent_value and '|' in opt.parent_value:
                    parts = opt.parent_value.split('|')
                    role = parts[0]
                    phone = parts[1]
                    display_name = f"{opt.value} - {role} ({phone})"
                else:
                    display_name = opt.value
                incharge_list.append((opt.value, display_name))
            incharge_list.sort(key=lambda x: x[1].lower())
            
        # Internal Choices
        internal_choices = [(a, a) for a in agency_list]
        
        # External choices (All departments except the current one)
        dept_qs = Department.objects.all().order_by('name')
        if department:
            dept_qs = dept_qs.exclude(id=department.id)
        external_choices = [(d.name, d.name) for d in dept_qs]
        
        # Combine choices so Django validation passes when any is chosen
        self.fields['agency'].choices = [('', 'Select Agency')] + internal_choices + external_choices
        self.fields['equipment'].choices = [('', 'Select Equipment')] + equip_list
        self.fields['sub_agency'].choices = [('', 'Select Area')] + [(sa, sa) for sa in sub_agency_list]
        self.fields['sub_agency'].label = 'Area'
        self.fields['sub_area'].choices = [('', 'Select Sub Area')] + [(sa, sa) for sa in sub_area_list]
        self.fields['sub_area'].label = 'Sub Area'
        self.fields['sub_equipment'].choices = [('', 'Select Sub Equipment')] + [(se, se) for se in sub_equip_list]
        self.fields['shift_incharge'].choices = [('', 'Select Shift Incharge')] + incharge_list
        
        # If editing an existing instance, preserve values and set initial agency_type
        if self.instance and self.instance.pk:
            self.initial['agency_type'] = self.instance.agency_type or 'Internal'
            
            def add_choice_if_missing(field_name, val):
                if not val:
                    return
                val_str = str(val).strip()
                if not val_str:
                    return
                choices = self.fields[field_name].choices
                # Check case-insensitively if val_str is already in the choice values
                if not any(str(c[0]).strip().lower() == val_str.lower() for c in choices):
                    self.fields[field_name].choices.append((val_str, val_str))

            add_choice_if_missing('agency', self.instance.agency)
            add_choice_if_missing('equipment', self.instance.equipment)
            add_choice_if_missing('sub_agency', self.instance.sub_agency)
            add_choice_if_missing('sub_area', self.instance.sub_area)
            add_choice_if_missing('sub_equipment', self.instance.sub_equipment)
            add_choice_if_missing('shift_incharge', self.instance.shift_incharge)
                
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            try:
                import re
                pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$')
                start_match = pattern.match(start_time.strip())
                end_match = pattern.match(end_time.strip())
                if start_match and end_match:
                    sh, sm = map(int, start_match.groups())
                    eh, em = map(int, end_match.groups())
                    start_mins = sh * 60 + sm
                    end_mins = eh * 60 + em
                    if end_mins < start_mins:
                        # midnight crossing
                        end_mins += 24 * 60
                    cleaned_data['duration_mins'] = float(end_mins - start_mins)
            except Exception:
                pass
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.agency:
            instance.agency = normalize_agency_name(instance.agency)
        if not instance.description:
            eq_name = instance.equipment or "Unknown Equipment"
            instance.description = f"Manual delay entry for {eq_name} ({instance.agency})"
        if commit:
            instance.save()
        return instance


