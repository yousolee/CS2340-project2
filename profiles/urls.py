from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.my_profile, name='profiles.me'),
    path('me/edit/', views.edit_profile, name='profiles.edit'),
    path('me/edit/<str:section>/', views.edit_profile_section, name='profiles.edit_section'),
    path('<str:username>/', views.public_profile, name='profiles.public'),
]
