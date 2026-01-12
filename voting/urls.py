from django.urls import path
from voting import views

app_name = 'voting'

urlpatterns = [
    path('favicon.svg', views.favicon, name='favicon'),
    path('media/<path:path>', views.serve_media, name='serve_media'),
    path('', views.index, name='index'),
    path('votacion/<int:voting_id>/', views.voting_detail, name='voting_detail'),
    path('votacion/<int:voting_id>/registro/', views.register, name='register'),
    path('votar/<int:subject_id>/', views.vote, name='vote'),
    path('exito/', views.success, name='success'),
    path('estadisticas/<int:voting_id>/', views.voting_statistics, name='statistics'),
]
