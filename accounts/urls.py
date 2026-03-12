from django.urls import path
from . import views

urlpatterns = [
    path('signup', views.signup, name='accounts.signup'),
    path('login/', views.login, name='accounts.login'),
    path('dashboard/', views.dashboard, name='accounts.dashboard'),
    path('logout/', views.logout, name='accounts.logout'),
    path('candidate-search/', views.candidate_search, name='accounts.candidate_search'),
    path('saved-searches/', views.saved_searches, name='accounts.saved_searches'),
    path('save-search/', views.save_search, name='accounts.save_search'),
    path('saved-searches/delete/<int:search_id>/', views.delete_saved_search, name='accounts.delete_saved_search'),
    path('applicant-map/', views.applicant_map, name='accounts.applicant_map'),

    # Admin Dashboard URLs
    path('admin-dashboard/', views.admin_dashboard, name='accounts.admin_dashboard'),
    path('admin-dashboard/users/', views.admin_users, name='accounts.admin_users'),
    path('admin-dashboard/users/toggle/<int:user_id>/', views.admin_toggle_user, name='accounts.admin_toggle_user'),
    path('admin-dashboard/jobs/', views.admin_jobs, name='accounts.admin_jobs'),
    path('admin-dashboard/jobs/delete/<int:job_id>/', views.admin_delete_job, name='accounts.admin_delete_job'),
    path('admin-dashboard/export/users/', views.admin_export_users, name='accounts.admin_export_users'),
    path('admin-dashboard/export/jobs/', views.admin_export_jobs, name='accounts.admin_export_jobs'),
    path('admin-dashboard/export/applications/', views.admin_export_applications, name='accounts.admin_export_applications'),
    path('recruiter/profile/', views.edit_recruiter_profile, name='accounts.edit_recruiter_profile'),
    path(
        'recruiter/profile/<str:section>/',
        views.edit_recruiter_profile_section,
        name='accounts.edit_recruiter_profile_section',
    ),
]
