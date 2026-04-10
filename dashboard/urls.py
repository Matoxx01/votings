from django.urls import path
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('request-password-reset/', views.request_password_reset, name='request_password_reset'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
    path('', views.dashboard, name='dashboard'),
    path('votaciones/', views.votings_management, name='votings_management'),
    path('votaciones/<int:voting_id>/', views.voting_detail, name='voting_detail'),
    path('votaciones/<int:voting_id>/delete/', views.delete_voting, name='delete_voting'),
    path('votaciones/<int:voting_id>/subjects/', views.subjects_management, name='subjects_management'),
    path('votaciones/<int:voting_id>/subjects/<int:subject_id>/delete/', views.delete_subject, name='delete_subject'),
    path('votaciones/<int:voting_id>/estadisticas/', views.voting_statistics, name='voting_statistics'),
    path('votaciones/<int:voting_id>/reporte/', views.generate_report, name='report'),
    path('usuarios/', views.user_data_management, name='user_data_management'),
    path('usuarios/cargar/', views.user_data_upload, name='user_data_upload'),
    path('militantes/invitar/', views.militante_invite, name='militante_invite'),
    path('maintainers/', views.maintainers_management, name='maintainers_management'),
    path('maintainers/create/', views.create_maintainer, name='create_maintainer'),
    path('maintainers/<int:maintainer_id>/edit/', views.edit_maintainer, name='edit_maintainer'),
    path('maintainers/<int:maintainer_id>/delete/', views.delete_maintainer, name='delete_maintainer'),
    path('maintainers/<int:maintainer_id>/send-password-reset/', views.send_password_reset_email, name='send_password_reset'),
]
