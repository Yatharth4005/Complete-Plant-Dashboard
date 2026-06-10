from django import forms
from cmc.models import OilTestLog

class OilTestLogForm(forms.ModelForm):
    class Meta:
        model = OilTestLog
        fields = ['equipment', 'date', 'viscosity', 'moisture', 'nas_class', 'test_no', 'status', 'notification_no', 'login_by', 'sent_date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'viscosity': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any'}),
            'moisture': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. <0.1% or <200ppm'}),
            'nas_class': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 11 or >12'}),
            'test_no': forms.NumberInput(attrs={'class': 'input-mono'}),
            'status': forms.Select(attrs={'class': 'input-mono'}),
            'notification_no': forms.TextInput(attrs={'class': 'input-mono'}),
            'login_by': forms.TextInput(attrs={'class': 'input-mono'}),
            'sent_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'remarks': forms.Textarea(attrs={'class': 'input-remarks', 'rows': 3}),
        }
