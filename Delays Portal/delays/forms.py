from django import forms
from delays.models import DelayRecord

class DelayRecordForm(forms.ModelForm):
    agency = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'input-mono'}))
    equipment = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))
    why = forms.ChoiceField(choices=[('WHY/WHY', 'WHY/WHY'), ('CAPA', 'CAPA'), ('NO', 'NO')], required=False, widget=forms.Select(attrs={'class': 'input-mono'}))

    class Meta:
        model = DelayRecord
        fields = ['date', 'duration_mins', 'agency', 'equipment', 'why']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'duration_mins': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any', 'placeholder': 'Duration in minutes'}),
        }

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        
        # Default choices if nothing in DB
        agency_list = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
        equip_list = []
        
        if department:
            records = DelayRecord.objects.filter(department=department)
            db_agencies = list(records.order_by('agency').values_list('agency', flat=True).distinct().exclude(agency=''))
            if db_agencies:
                agency_list = db_agencies
            equip_list = list(records.order_by('equipment').values_list('equipment', flat=True).distinct().exclude(equipment=''))
            
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

