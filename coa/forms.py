from django import forms
from .models import COA, Category


class COAForm(forms.ModelForm):
    class Meta:
        model  = COA
        # ar_no REMOVED (Change 5)
        fields = [
            'product_name',
            'category',
            'botanical_name',
            'plant_part',
            'customer_name',
            'manufacturing_date',
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={
                'placeholder': 'Type or select item name...',
                'id': 'id_product_name',
                'autocomplete': 'off',
            }),
            'category': forms.Select(attrs={'id': 'id_category'}),
            'botanical_name': forms.TextInput(attrs={
                'placeholder': 'Auto-filled from item database (editable)',
                'id': 'id_botanical_name',
            }),
            'plant_part': forms.TextInput(attrs={
                'placeholder': 'Auto-filled from item database (editable)',
                'id': 'id_plant_part',
            }),
            'customer_name': forms.TextInput(attrs={
                'placeholder': 'Type or select customer (for records only)...',
                'id': 'id_customer_name',
                'autocomplete': 'off',
            }),
            'manufacturing_date': forms.DateInput(attrs={
                'type': 'date',
                'id': 'id_manufacturing_date',
            }),
        }