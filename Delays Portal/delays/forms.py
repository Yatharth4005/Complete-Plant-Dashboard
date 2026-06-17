from django import forms
from delays.models import DelayRecord, DelayDropdownOption

class DelayRecordForm(forms.ModelForm):
    agency = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'input-mono'}))
    equipment = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    why = forms.ChoiceField(choices=[('CAPA', 'CAPA'), ('NO', 'NO')], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'input-mono', 'rows': 3, 'placeholder': 'Detailed description of the delay/breakdown'}))

    class Meta:
        model = DelayRecord
        fields = [
            'date', 'time_slot', 'start_time', 'end_time', 'duration_mins',
            'agency', 'sub_agency', 'section', 'equipment', 'sub_equipment',
            'shift_incharge', 'description', 'why'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'time_slot': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:00 - 23:00'}),
            'start_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:15'}),
            'end_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:25'}),
            'duration_mins': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any', 'placeholder': 'Duration in minutes'}),
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
            
        self.fields['agency'].choices = [(a, a) for a in agency_list]
        self.fields['equipment'].choices = [('', 'Select Equipment')] + [(e, e) for e in equip_list]
        
        # If editing an existing instance, make sure its current values are valid choices
        if self.instance and self.instance.pk:
            if self.instance.agency and (self.instance.agency, self.instance.agency) not in self.fields['agency'].choices:
                self.fields['agency'].choices.append((self.instance.agency, self.instance.agency))
            if self.instance.equipment and (self.instance.equipment, self.instance.equipment) not in self.fields['equipment'].choices:
                self.fields['equipment'].choices.append((self.instance.equipment, self.instance.equipment))
                
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.description:
            eq_name = instance.equipment or "Unknown Equipment"
            instance.description = f"Manual delay entry for {eq_name} ({instance.agency})"
        if commit:
            instance.save()
        return instance

