from django import forms
from cmc.models import WDALog

class WDALogForm(forms.ModelForm):
    class Meta:
        model = WDALog
        fields = ['equipment', 'date', 'ratio', 'dl', 'ds', 'wpc', 'slide', 'checked_by', 'final_status', 'notification_no', 'sent_login', 'sent_date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'ratio': forms.TextInput(attrs={'class': 'input-mono', 'placeholder': 'e.g. 1:10 or 1:100'}),
            'dl': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any'}),
            'ds': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any'}),
            'wpc': forms.NumberInput(attrs={'class': 'input-mono', 'step': 'any'}),
            'slide': forms.TextInput(attrs={'class': 'input-mono'}),
            'checked_by': forms.TextInput(attrs={'class': 'input-mono'}),
            'final_status': forms.Select(attrs={'class': 'input-mono'}),
            'notification_no': forms.TextInput(attrs={'class': 'input-mono'}),
            'sent_login': forms.TextInput(attrs={'class': 'input-mono'}),
            'sent_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-mono'}),
            'remarks': forms.Textarea(attrs={'class': 'input-remarks', 'rows': 3}),
        }
