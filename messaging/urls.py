from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='messaging.inbox'),
    path('<int:conversation_id>/', views.conversation_detail, name='messaging.conversation'),
    path('start/<str:username>/', views.start_conversation, name='messaging.start'),
    path('email/<str:username>/', views.send_email_to_user, name='messaging.send_email'),
]
