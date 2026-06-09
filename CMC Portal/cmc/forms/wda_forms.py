from django import forms
from cmc.models import WDALog

class WDALogForm(forms.ModelForm):
    class Meta:
        model = WDALog
        fields = ['equipment', 'date', 'ratio', 'dl', 'ds', 'wpc', 'slide', 'checked_by', 'final_status', 'notification_no', 'sent_login', 'sent_date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ratio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1:10 or 1:100'}),
            'dl': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'ds': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'wpc': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'slide': forms.TextInput(attrs={'class': 'form-control'}),
            'checked_by': forms.TextInput(attrs={'class': 'form-control'}),
            'final_status': forms.Select(attrs={'class': 'form-select'}),
            'notification_no': forms.TextInput(attrs={'class': 'form-control'}),
            'sent_login': forms.TextInput(attrs={'class': 'form-control'}),
            'sent_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
