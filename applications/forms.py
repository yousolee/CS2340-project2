from django import forms

from .models import Application


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['note', 'resume']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 6}),
        }


class ApplicationFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All stages'), *Application.Status.choices],
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    job = forms.ChoiceField(
        required=False,
        choices=[('', 'All jobs')],
    )

    def __init__(self, *args, **kwargs):
        job_choices = kwargs.pop('job_choices', None)
        super().__init__(*args, **kwargs)
        if job_choices is not None:
            self.fields['job'].choices = [('', 'All jobs'), *job_choices]
        for field_name in ("status", "date_from", "date_to", "job"):
            self.fields[field_name].widget.attrs.update({"class": "form-control"})
