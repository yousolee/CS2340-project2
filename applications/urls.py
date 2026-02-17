from django.urls import path

from . import views

app_name = 'applications'

urlpatterns = [
    path('apply/<int:job_id>/', views.apply_for_job, name='apply'),
    path('<int:pk>/update-status/', views.update_application_status, name='update_status'),
    path('<int:pk>/', views.application_detail, name='detail'),
    path('', views.application_list, name='list'),
]
