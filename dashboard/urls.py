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
    path('usuarios/<str:rut>/editar/', views.edit_user_data, name='edit_user_data'),
    path('usuarios/api/status/', views.user_statuses_api, name='user_statuses_api'),
    path('usuarios/api/search/', views.user_data_search_api, name='user_data_search_api'),
    path('usuarios/cargar/', views.user_data_upload, name='user_data_upload'),
    path('militantes/invitar/', views.militante_invite, name='militante_invite'),
    path('reporte-votantes/', views.voters_report, name='voters_report'),
    path('reporte-votantes/api/data/', views.voters_report_data_api, name='voters_report_data_api'),
    path('maintainers/', views.maintainers_management, name='maintainers_management'),
    path('maintainers/create/', views.create_maintainer, name='create_maintainer'),
    path('maintainers/<int:maintainer_id>/edit/', views.edit_maintainer, name='edit_maintainer'),
    path('maintainers/<int:maintainer_id>/delete/', views.delete_maintainer, name='delete_maintainer'),
    path('maintainers/<int:maintainer_id>/send-password-reset/', views.send_password_reset_email, name='send_password_reset'),
    path('logs/cargas/', views.data_upload_logs, name='data_upload_logs'),
    path('logs/cargas/reanudar/', views.resume_stuck_uploads, name='resume_stuck_uploads'),
    # Gestión de Documentos (Biblioteca)
    path('documentos/', views.documents_management, name='documents_management'),
    path('documentos/secciones/crear/', views.create_document_section, name='create_document_section'),
    path('documentos/secciones/<int:section_id>/editar/', views.edit_document_section, name='edit_document_section'),
    path('documentos/secciones/<int:section_id>/eliminar/', views.delete_document_section, name='delete_document_section'),
    path('documentos/secciones/<int:section_id>/subir/', views.upload_document, name='upload_document'),
    path('documentos/<int:document_id>/editar/', views.edit_document, name='edit_document'),
    path('documentos/<int:document_id>/eliminar/', views.delete_document, name='delete_document'),
    path('documentos/ordenar/', views.reorder_documents, name='reorder_documents'),
    
    # Gestión de FAQ
    path('faq/', views.faq_management, name='faq_management'),
    path('faq/crear/', views.create_faq, name='create_faq'),
    path('faq/<int:faq_id>/editar/', views.edit_faq, name='edit_faq'),
    path('faq/<int:faq_id>/eliminar/', views.delete_faq, name='delete_faq'),
    
    # Gestión de Llaves USB
    path('llaves-usb/', views.access_keys_management, name='access_keys_management'),
    path('llaves-usb/api/generar/', views.api_generate_key, name='api_generate_key'),
    path('llaves-usb/<int:key_id>/eliminar/', views.delete_access_key, name='delete_access_key'),
    
    path('reporte-votantes/api/data/', views.voters_report_data_api, name='voters_report_data_api'),
    path('maintainers/', views.maintainers_management, name='maintainers_management'),
    path('maintainers/create/', views.create_maintainer, name='create_maintainer'),
    path('maintainers/<int:maintainer_id>/edit/', views.edit_maintainer, name='edit_maintainer'),
    path('maintainers/<int:maintainer_id>/delete/', views.delete_maintainer, name='delete_maintainer'),
    path('maintainers/<int:maintainer_id>/send-password-reset/', views.send_password_reset_email, name='send_password_reset'),
    path('logs/cargas/', views.data_upload_logs, name='data_upload_logs'),
    path('logs/cargas/reanudar/', views.resume_stuck_uploads, name='resume_stuck_uploads'),
    # Gestión de Documentos (Biblioteca)
    path('documentos/', views.documents_management, name='documents_management'),
    path('documentos/secciones/crear/', views.create_document_section, name='create_document_section'),
    path('documentos/secciones/<int:section_id>/editar/', views.edit_document_section, name='edit_document_section'),
    path('documentos/secciones/<int:section_id>/eliminar/', views.delete_document_section, name='delete_document_section'),
    path('documentos/secciones/<int:section_id>/subir/', views.upload_document, name='upload_document'),
    path('documentos/<int:document_id>/editar/', views.edit_document, name='edit_document'),
    path('documentos/<int:document_id>/eliminar/', views.delete_document, name='delete_document'),
    path('documentos/ordenar/', views.reorder_documents, name='reorder_documents'),
    
    # Gestión de FAQ
    path('faq/', views.faq_management, name='faq_management'),
    path('faq/crear/', views.create_faq, name='create_faq'),
    path('faq/<int:faq_id>/editar/', views.edit_faq, name='edit_faq'),
    path('faq/<int:faq_id>/eliminar/', views.delete_faq, name='delete_faq'),
    
    # Gestión de Llaves USB
    path('llaves-usb/', views.access_keys_management, name='access_keys_management'),
    path('llaves-usb/api/generar/', views.api_generate_key, name='api_generate_key'),
    path('llaves-usb/<int:key_id>/eliminar/', views.delete_access_key, name='delete_access_key'),
    
    # Centro de Seguridad
    path('seguridad/', views.security_center, name='security_center'),
    path('seguridad/verificar-cadena/<int:voting_id>/', views.verify_chain_api, name='verify_chain_api'),
    path('seguridad/bloquear-ip/', views.block_ip_api, name='block_ip_api'),
    path('seguridad/desbloquear-ip/<int:block_id>/', views.unblock_ip_api, name='unblock_ip_api'),
    path('seguridad/usuario-info/', views.security_user_info_api, name='security_user_info_api'),
    path('seguridad/eventos/exportar/', views.export_security_events, name='export_security_events'),
    
    # Pruebas del Sistema
    path('pruebas/', views.system_tests, name='system_tests'),
    path('pruebas/api/registro-civil/', views.test_registro_civil_api, name='test_registro_civil_api'),
]
