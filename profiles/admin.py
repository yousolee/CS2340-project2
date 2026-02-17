from django.contrib import admin

from .models import Education, Experience, Profile


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "headline", "location", "updated_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "headline")
    inlines = [ExperienceInline, EducationInline]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "company", "start_date", "end_date", "is_current")
    search_fields = ("title", "company", "profile__user__username")


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("profile", "school", "degree", "start_date", "end_date", "is_current")
    search_fields = ("school", "degree", "profile__user__username")
