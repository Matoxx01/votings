from django.urls import path
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('votaciones/', views.votings_management, name='votings_management'),
    path('votaciones/<int:voting_id>/', views.voting_detail, name='voting_detail'),
    path('votaciones/<int:voting_id>/subjects/', views.subjects_management, name='subjects_management'),
    path('votaciones/<int:voting_id>/estadisticas/', views.voting_statistics, name='voting_statistics'),
    path('votaciones/<int:voting_id>/reporte/', views.generate_report, name='report'),
    path('usuarios/', views.user_data_management, name='user_data_management'),
    path('maintainers/', views.maintainers_management, name='maintainers_management'),
]
