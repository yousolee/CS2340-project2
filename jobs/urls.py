from django.urls import path
from . import views

urlpatterns = [
    path("", views.job_list, name='jobs.list'),
    path('search/', views.job_search, name='jobs.search'),
    path('create/', views.create_job, name='jobs.create'),
    path('my-postings/', views.my_postings, name='jobs.my_postings'),
    path("<int:job_id>/", views.job_detail, name='jobs.detail'),
]
