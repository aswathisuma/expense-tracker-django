from django import forms

from .models import Expense


class ExpenseForm(forms.ModelForm):
    """Form used for both adding and editing an expense."""

    class Meta:
        model = Expense
        fields = ['title', 'amount', 'category', 'date', 'description']
        labels = {
            'title': 'Expense Title',
            'amount': 'Amount (₹)',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Lunch'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            # type="date" shows the browser's date picker; the format must be YYYY-MM-DD
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than 0.')
        return amount
