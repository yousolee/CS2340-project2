from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='messaging.inbox'),
    path('<int:conversation_id>/', views.conversation_detail, name='messaging.conversation'),
    path('start/<str:username>/', views.start_conversation, name='messaging.start'),
]
