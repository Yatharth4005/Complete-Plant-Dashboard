from django import forms
from cmc.models import GreaseReportLog

class GreaseReportLogForm(forms.ModelForm):
    class Meta:
        model = GreaseReportLog
        fields = ['equipment', 'date', 'ferrocheck', 'status', 'sent_date', 'login', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'ferrocheck': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any', 'placeholder': 'e.g. 15.0'}),
            'status': forms.Select(attrs={'class': 'input-mono'}),
            'login': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'Initials, e.g. PKA'}),
            'sent_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'remarks': forms.Textarea(attrs={'class': 'input-remarks', 'rows': 3, 'placeholder': 'Add details...'}),
        }
