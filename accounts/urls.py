from django.urls import path
from . import views

urlpatterns = [
    path('signup', views.signup, name='accounts.signup'),
    path('login/', views.login, name='accounts.login'),
    path('dashboard/', views.dashboard, name='accounts.dashboard'),
    path('logout/', views.logout, name='accounts.logout'),
    path('candidate-search/', views.candidate_search, name='accounts.candidate_search'),
]
