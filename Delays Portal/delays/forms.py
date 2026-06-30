from django import forms
from tpm.models import Department
from delays.models import DelayRecord, DelayDropdownOption
from delays.utils.parser import normalize_agency_name

class DelayRecordForm(forms.ModelForm):
    agency_type = forms.ChoiceField(
        choices=[('Internal', 'Internal'), ('External', 'External')],
        required=True,
        widget=forms.Select(attrs={'class': 'input-mono', 'id': 'id_agency_type'})
    )
    agency = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'input-mono', 'id': 'id_agency'}))
    sub_agency = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    equipment = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    sub_equipment = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    shift_incharge = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    why = forms.ChoiceField(choices=[('CAPA', 'CAPA'), ('NO', 'NO')], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
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

    class Meta:
        model = DelayRecord
        fields = [
            'date', 'start_time', 'end_time', 'duration_mins',
            'agency_type', 'agency', 'sub_agency', 'equipment', 'sub_equipment',
            'shift_incharge', 'description', 'why'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'start_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:15', 'id': 'id_start_time'}),
            'end_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:25', 'id': 'id_end_time'}),
        }

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        
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
            
            if not equip_list:
                db_equipments = sorted(list(DelayRecord.objects.filter(department=department).exclude(equipment__isnull=True).exclude(equipment='').exclude(equipment='NIL').values_list('equipment', flat=True).distinct()))
                equip_list = [(eq, eq) for eq in db_equipments]
            else:
                equip_list.sort(key=lambda x: x[0])
                
            # Fetch sub-agencies from dropdown options + unique past values
            sub_agencies_set = set(DelayDropdownOption.objects.filter(
                department=department, category__iexact='Sub-Agency'
            ).values_list('value', flat=True).distinct())
            sub_agencies_set.update(DelayRecord.objects.filter(department=department).exclude(sub_agency__isnull=True).exclude(sub_agency='').values_list('sub_agency', flat=True).distinct())
            sub_agency_list = sorted([x for x in sub_agencies_set if x])

            # Fetch sub-equipments from dropdown options + unique past values
            sub_equip_set = set(DelayDropdownOption.objects.filter(
                department=department, category__iexact='Sub-Equipment'
            ).values_list('value', flat=True).distinct())
            sub_equip_set.update(DelayRecord.objects.filter(department=department).exclude(sub_equipment__isnull=True).exclude(sub_equipment='').values_list('sub_equipment', flat=True).distinct())
            sub_equip_list = sorted([x for x in sub_equip_set if x])

            # Fetch shift incharges from unique past values
            incharge_set = set(DelayRecord.objects.filter(department=department).exclude(shift_incharge__isnull=True).exclude(shift_incharge='').values_list('shift_incharge', flat=True).distinct())
            incharge_list = sorted([x for x in incharge_set if x])
            
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
        self.fields['sub_agency'].choices = [('', 'Select Sub Agency')] + [(sa, sa) for sa in sub_agency_list]
        self.fields['sub_equipment'].choices = [('', 'Select Sub Equipment')] + [(se, se) for se in sub_equip_list]
        self.fields['shift_incharge'].choices = [('', 'Select Shift Incharge')] + [(inc, inc) for inc in incharge_list]
        
        # If editing an existing instance, preserve values and set initial agency_type
        if self.instance and self.instance.pk:
            self.initial['agency_type'] = self.instance.agency_type or 'Internal'
            if self.instance.agency and (self.instance.agency, self.instance.agency) not in self.fields['agency'].choices:
                self.fields['agency'].choices.append((self.instance.agency, self.instance.agency))
            if self.instance.equipment and not any(c[0] == self.instance.equipment for c in self.fields['equipment'].choices):
                self.fields['equipment'].choices.append((self.instance.equipment, self.instance.equipment))
            if self.instance.sub_agency and (self.instance.sub_agency, self.instance.sub_agency) not in self.fields['sub_agency'].choices:
                self.fields['sub_agency'].choices.append((self.instance.sub_agency, self.instance.sub_agency))
            if self.instance.sub_equipment and (self.instance.sub_equipment, self.instance.sub_equipment) not in self.fields['sub_equipment'].choices:
                self.fields['sub_equipment'].choices.append((self.instance.sub_equipment, self.instance.sub_equipment))
            if self.instance.shift_incharge and (self.instance.shift_incharge, self.instance.shift_incharge) not in self.fields['shift_incharge'].choices:
                self.fields['shift_incharge'].choices.append((self.instance.shift_incharge, self.instance.shift_incharge))
                
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


