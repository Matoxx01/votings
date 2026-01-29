from django.urls import path
from voting import views

app_name = 'voting'

urlpatterns = [
    path('favicon.svg', views.favicon, name='favicon'),
    path('media/<path:path>', views.serve_media, name='serve_media'),
    path('', views.index, name='index'),
    path('region/<int:region_id>/', views.region_votings, name='region_votings'),
    path('votacion/<int:voting_id>/', views.voting_detail, name='voting_detail'),
    path('votacion/<int:voting_id>/registro/', views.register, name='register'),
    path('votacion/<int:voting_id>/login/', views.militante_login, name='militante_login'),
    path('votacion/<int:voting_id>/olvide-contrasena/', views.militante_password_reset_request, name='militante_password_reset_request'),
    path('militante-logout/', views.militante_logout, name='militante_logout'),
    path('votar/<int:subject_id>/', views.vote, name='vote'),
    path('exito/', views.success, name='success'),
    path('estadisticas/<int:voting_id>/', views.voting_statistics, name='statistics'),
    # Rutas de militantes
    path('registro-militante/<str:token>/', views.militante_register, name='militante_register'),
    path('recuperar-contrasena-militante/<str:token>/', views.militante_password_reset, name='militante_password_reset'),
]
