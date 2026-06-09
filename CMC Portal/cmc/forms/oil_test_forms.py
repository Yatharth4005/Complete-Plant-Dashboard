from django import forms
from cmc.models import OilTestLog

class OilTestLogForm(forms.ModelForm):
    class Meta:
        model = OilTestLog
        fields = ['equipment', 'date', 'viscosity', 'moisture', 'nas_class', 'test_no', 'status', 'notification_no', 'login_by', 'sent_date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'viscosity': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'moisture': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. <0.1% or <200ppm'}),
            'nas_class': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 11 or >12'}),
            'test_no': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notification_no': forms.TextInput(attrs={'class': 'form-control'}),
            'login_by': forms.TextInput(attrs={'class': 'form-control'}),
            'sent_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
