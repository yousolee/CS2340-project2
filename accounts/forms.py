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
