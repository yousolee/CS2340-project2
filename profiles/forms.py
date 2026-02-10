from django import forms
from django.forms import inlineformset_factory

from .models import Education, Experience, Profile

BASE_PROFILE_WIDGETS = {
    "headline": forms.TextInput(
        attrs={"class": "form-control", "maxlength": 160, "placeholder": "Headline"}
    ),
    "location": forms.TextInput(
        attrs={
            "class": "form-control",
            "maxlength": 120,
            "placeholder": "City, State, Country",
        }
    ),
    "summary": forms.Textarea(
        attrs={
            "class": "form-control",
            "rows": 4,
            "maxlength": 1000,
            "placeholder": "Write a short professional summary.",
        }
    ),
    "skills": forms.Textarea(
        attrs={
            "class": "form-control",
            "rows": 3,
            "maxlength": 600,
            "placeholder": "Python, Django, SQL, Data Analysis, ...",
        }
    ),
    "links": forms.Textarea(
        attrs={
            "class": "form-control",
            "rows": 3,
            "maxlength": 1000,
            "placeholder": "https://www.linkedin.com/in/you",
        }
    ),
}


class BasicProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["headline", "location"]
        widgets = {
            "headline": BASE_PROFILE_WIDGETS["headline"],
            "location": BASE_PROFILE_WIDGETS["location"],
        }


class AboutProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["summary"]
        widgets = {
            "summary": BASE_PROFILE_WIDGETS["summary"],
        }


class SkillsProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["skills"]
        widgets = {
            "skills": BASE_PROFILE_WIDGETS["skills"],
        }


class LinksProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["links"]
        widgets = {
            "links": BASE_PROFILE_WIDGETS["links"],
        }


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        exclude = ["profile", "created_at"]
        widgets = {
            "company": forms.TextInput(attrs={"class": "form-control", "maxlength": 120}),
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": 120}),
            "employment_type": forms.Select(attrs={"class": "form-select"}),
            "location": forms.TextInput(attrs={"class": "form-control", "maxlength": 120}),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "maxlength": 1000}
            ),
            "activities": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "maxlength": 600}
            ),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        exclude = ["profile", "created_at"]
        widgets = {
            "school": forms.TextInput(attrs={"class": "form-control", "maxlength": 120}),
            "degree": forms.TextInput(attrs={"class": "form-control", "maxlength": 120}),
            "field_of_study": forms.TextInput(attrs={"class": "form-control", "maxlength": 120}),
            "enrollment_type": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "grade": forms.TextInput(attrs={"class": "form-control", "maxlength": 40}),
            "activities": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "maxlength": 600}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "maxlength": 1000}
            ),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


ExperienceFormSet = inlineformset_factory(
    Profile,
    Experience,
    form=ExperienceForm,
    extra=1,
    can_delete=True,
)

EducationFormSet = inlineformset_factory(
    Profile,
    Education,
    form=EducationForm,
    extra=1,
    can_delete=True,
)
