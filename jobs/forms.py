from django import forms

from .models import Job


class JobSearchForm(forms.Form):
    title = forms.CharField(required=False)
    skills = forms.CharField(required=False)
    location = forms.CharField(required=False)
    min_salary = forms.DecimalField(required=False)
    max_salary = forms.DecimalField(required=False)
    mode = forms.ChoiceField(
        required=False,
        choices = [('', 'Any'), ('remote', 'Remote'), ('onsite', 'On-Site'), ('hybrid', 'Hybrid')]
    )
    visa_sponsorship = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(JobSearchForm, self).__init__(*args, **kwargs)

        for fieldname in ['title', 'skills', 'location', 'min_salary', 'max_salary']:
            self.fields[fieldname].widget.attrs.update({'class' : 'form-control'})
        
        self.fields['title'].widget.attrs.update({'placeholder': 'Job title'})
        self.fields['skills'].widget.attrs.update({'placeholder': 'Skills (i.e., Python, Django)'})
        self.fields['location'].widget.attrs.update({'placeholder': 'Location'})
        self.fields['min_salary'].widget.attrs.update({'placeholder': 'Min salary'})
        self.fields['max_salary'].widget.attrs.update({'placeholder': 'Max salary'})
        self.fields['mode'].widget.attrs.update({'class': 'form-select'})        
        self.fields['visa_sponsorship'].widget.attrs.update({'class': 'form-check-input'})


class JobCreateForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title',
            'company',
            'location',
            'description',
            'skills',
            'min_salary',
            'max_salary',
            'mode',
            'visa_sponsorship',
        ]

    def __init__(self, *args, **kwargs):
        super(JobCreateForm, self).__init__(*args, **kwargs)
        for fieldname in [
            'title',
            'company',
            'location',
            'description',
            'skills',
            'min_salary',
            'max_salary',
        ]:
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})
        self.fields['mode'].widget.attrs.update({'class': 'form-select'})
        self.fields['visa_sponsorship'].widget.attrs.update({'class': 'form-check-input'})
