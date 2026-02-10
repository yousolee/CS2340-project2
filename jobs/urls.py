from django.urls import path
from . import views

urlpatterns = [
    path("", views.job_list, name='jobs.list'),
    path('search/', views.job_search, name='jobs.search'),
    path("<int:job_id>/", views.job_detail, name='jobs.detail'),
]