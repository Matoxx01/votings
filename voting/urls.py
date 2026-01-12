from django.urls import path
from voting import views

app_name = 'voting'

urlpatterns = [
    path('', views.index, name='index'),
    path('votacion/<int:voting_id>/', views.voting_detail, name='voting_detail'),
    path('votar/<int:subject_id>/', views.vote, name='vote'),
    path('exito/', views.success, name='success'),
    path('estadisticas/<int:voting_id>/', views.voting_statistics, name='statistics'),
]
