from django import forms
from delays.models import DelayRecord

class DelayRecordForm(forms.ModelForm):
    class Meta:
        model = DelayRecord
        fields = [
            'date', 'time_slot', 'start_time', 'end_time', 
            'duration_mins', 'agency', 'sub_agency', 'section', 
            'equipment', 'sub_equipment', 'shift_incharge', 
            'description', 'why'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'time_slot': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:00 - 23:00'}),
            'start_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:15'}),
            'end_time': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 22:25'}),
            'duration_mins': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any', 'placeholder': 'Duration in minutes'}),
            
            # Autocomplete standard list inputs
            'agency': forms.TextInput(attrs={'class': 'input-mono', 'list': 'agency_list', 'placeholder': 'Select or type agency'}),
            'sub_agency': forms.TextInput(attrs={'class': 'input-mono', 'list': 'sub_agency_list', 'placeholder': 'Select or type sub-agency'}),
            'section': forms.TextInput(attrs={'class': 'input-mono', 'list': 'section_list', 'placeholder': 'e.g. UC 254X254'}),
            'equipment': forms.TextInput(attrs={'class': 'input-mono', 'list': 'equipment_list', 'placeholder': 'Select or type equipment'}),
            'sub_equipment': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'Sub-equipment (optional)'}),
            'shift_incharge': forms.TextInput(attrs={'class': 'input-mono', 'list': 'incharge_list', 'placeholder': 'Shift incharge'}),
            
            # Text areas
            'description': forms.Textarea(attrs={'class': 'input-mono', 'rows': 3, 'placeholder': 'Enter detailed description of the delay...'}),
            'why': forms.Textarea(attrs={'class': 'input-mono', 'rows': 2, 'placeholder': 'Enter root cause or why-why analysis...'}),
        }
