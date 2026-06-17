from django import forms
from tpm.models import Department
from delays.models import DelayRecord, DelayDropdownOption

class DelayRecordForm(forms.ModelForm):
    agency_type = forms.ChoiceField(
        choices=[('Internal', 'Internal'), ('External', 'External')],
        required=True,
        widget=forms.Select(attrs={'class': 'input-mono', 'id': 'id_agency_type'})
    )
    agency = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'input-mono', 'id': 'id_agency'}))
    equipment = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
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
            'agency_type', 'agency', 'sub_agency', 'section', 'equipment', 'sub_equipment',
            'shift_incharge', 'description', 'why'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'start_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:15', 'id': 'id_start_time'}),
            'end_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:25', 'id': 'id_end_time'}),
            'sub_agency': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'Sub-agency', 'list': 'sub_agencies_list'}),
            'section': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'Rolled section', 'list': 'sections_list'}),
            'sub_equipment': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'Sub-equipment', 'list': 'sub_equipments_list'}),
            'shift_incharge': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'Shift Incharge', 'list': 'incharges_list'}),
        }

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        
        # Default choices if nothing in DB
        agency_list = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
        equip_list = []
        
        if department:
            # Fetch custom agencies from dropdown options
            agency_list = sorted(list(DelayDropdownOption.objects.filter(
                department=department, category__iexact='Agency'
            ).values_list('value', flat=True).distinct()))
            if not agency_list:
                agency_list = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']

            # Fetch custom equipments from dropdown options
            equip_list = sorted(list(DelayDropdownOption.objects.filter(
                department=department, category__iexact='Equipment'
            ).values_list('value', flat=True).distinct()))
            
        # Internal Choices
        internal_choices = [(a, a) for a in agency_list]
        
        # External choices (All departments except the current one)
        dept_qs = Department.objects.all().order_by('name')
        if department:
            dept_qs = dept_qs.exclude(id=department.id)
        external_choices = [(d.name, d.name) for d in dept_qs]
        
        # Combine choices so Django validation passes when any is chosen
        self.fields['agency'].choices = [('', 'Select Agency')] + internal_choices + external_choices
        self.fields['equipment'].choices = [('', 'Select Equipment')] + [(e, e) for e in equip_list]
        
        # If editing an existing instance, preserve values and set initial agency_type
        if self.instance and self.instance.pk:
            self.initial['agency_type'] = self.instance.agency_type or 'Internal'
            if self.instance.agency and (self.instance.agency, self.instance.agency) not in self.fields['agency'].choices:
                self.fields['agency'].choices.append((self.instance.agency, self.instance.agency))
            if self.instance.equipment and (self.instance.equipment, self.instance.equipment) not in self.fields['equipment'].choices:
                self.fields['equipment'].choices.append((self.instance.equipment, self.instance.equipment))
                
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
        if not instance.description:
            eq_name = instance.equipment or "Unknown Equipment"
            instance.description = f"Manual delay entry for {eq_name} ({instance.agency})"
        if commit:
            instance.save()
        return instance


