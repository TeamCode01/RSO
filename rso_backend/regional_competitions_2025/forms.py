from dal import autocomplete
from django import forms

from regional_competitions_2025.models import ExpertRole


class ExpertUserForm(forms.ModelForm):
    class Meta:
        model = ExpertRole
        fields = '__all__'
        widgets = {
            'user': autocomplete.ModelSelect2(url='user-autocomplete'),
        }
