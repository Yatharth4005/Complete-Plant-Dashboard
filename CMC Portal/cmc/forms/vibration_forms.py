from django import forms
from cmc.models import VibrationLog

class VibrationLogForm(forms.ModelForm):
    class Meta:
        model = VibrationLog
        fields = ['equipment', 'date', 'time', 'instrument', 'report_type', 'stored_in', 'reported_through', 'status', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'instrument': forms.Select(attrs={'class': 'form-select'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'stored_in': forms.TextInput(attrs={'class': 'form-control'}),
            'reported_through': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
