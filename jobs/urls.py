from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.job_search, name='jobs.search')
]