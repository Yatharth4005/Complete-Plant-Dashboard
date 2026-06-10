from django import forms
from cmc.models import VibrationLog

class VibrationLogForm(forms.ModelForm):
    class Meta:
        model = VibrationLog
        fields = ['equipment', 'date', 'time', 'instrument', 'report_type', 'stored_in', 'reported_through', 'status', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'input-mono'}),
            'instrument': forms.Select(attrs={'class': 'input-mono'}),
            'report_type': forms.Select(attrs={'class': 'input-mono'}),
            'stored_in': forms.TextInput(attrs={'class': 'input-mono'}),
            'reported_through': forms.TextInput(attrs={'class': 'input-mono'}),
            'status': forms.Select(attrs={'class': 'input-mono'}),
            'remarks': forms.Textarea(attrs={'class': 'input-remarks', 'rows': 3}),
        }
