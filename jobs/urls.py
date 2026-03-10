from django.urls import path
from . import views

urlpatterns = [
    path("", views.job_list, name='jobs.list'),
    path('map/', views.job_map, name='jobs.map'),
    path('create/', views.create_job, name='jobs.create'),
    path('my-postings/', views.my_postings, name='jobs.my_postings'),
    path('<int:job_id>/edit/', views.edit_job, name='jobs.edit'),
    path("<int:job_id>/", views.job_detail, name='jobs.detail'),
]
