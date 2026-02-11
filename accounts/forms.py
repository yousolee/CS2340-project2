from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe

from .models import Recruiter


class CustomErrorList(ErrorList):
    def __str__(self):
        if not self:
            return ''
        return mark_safe(''.join([
            f'<div class="alert alert-danger" role="alert">{e}</div>'
            for e in self
        ]))

class CustomUserCreationForm(UserCreationForm):
    ACCOUNT_TYPE_CHOICES = [
        ('job_seeker', 'Job Seeker'),
        ('recruiter', 'Recruiter'),
    ]

    account_type = forms.ChoiceField(
        choices=ACCOUNT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='job_seeker',
    )
    company_name = forms.CharField(
        required=False,
        max_length=200,
        help_text='Optional (used for recruiter accounts).',
    )

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        for fieldname in ['username', 'password1', 'password2', 'company_name']:
            self.fields[fieldname].help_text = None
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=commit)
        account_type = self.cleaned_data.get('account_type')
        company_name = self.cleaned_data.get('company_name', '').strip()

        if account_type == 'recruiter':
            Recruiter.objects.get_or_create(
                user=user,
                defaults={'company_name': company_name},
            )

        return user
    
class CandidateSearchForm(forms.Form):
    skills = forms.CharField(required=False)
    location = forms.CharField(required=False)
    company = forms.CharField(required=False)
    job_title = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(CandidateSearchForm, self).__init__(*args, **kwargs)

        for fieldname in ['skills', 'location', 'company', 'job_title']:
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})
        
        self.fields['skills'].widget.attrs.update({'placeholder': 'Skills (e.g. Python, Django)'})
        self.fields['location'].widget.attrs.update({'placeholder': 'Location'})
        self.fields['company'].widget.attrs.update({'placeholder': 'Company'})
        self.fields['job_title'].widget.attrs.update({'placeholder': 'Job Title'})
