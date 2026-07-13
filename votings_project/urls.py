"""
URL configuration for votings_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("voting.urls")),
    path("dashboard/", include("dashboard.urls")),
]

# Servir archivos estáticos y media en desarrollo
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

handler404 = 'votings_project.views.custom_404'

from django.urls import re_path
from django.views.static import serve

from django.http import HttpResponse
import os

def check_media(request):
    media_path = str(settings.MEDIA_ROOT)
    seed_path = str(settings.BASE_DIR / "media_seed")
    output = f"Media Root: {media_path}<br>"
    output += f"Exists: {os.path.exists(media_path)}<br>"
    if os.path.exists(media_path):
        output += f"Contents: {os.listdir(media_path)}<br>"
        if os.path.exists(os.path.join(media_path, "documentos")):
            output += f"Documentos: {os.listdir(os.path.join(media_path, 'documentos'))}<br>"
            
    output += f"<br>Seed Root: {seed_path}<br>"
    output += f"Exists: {os.path.exists(seed_path)}<br>"
    if os.path.exists(seed_path):
        output += f"Contents: {os.listdir(seed_path)}<br>"
        if os.path.exists(os.path.join(seed_path, "documentos")):
            output += f"Documentos: {os.listdir(os.path.join(seed_path, 'documentos'))}<br>"
    return HttpResponse(output)

urlpatterns += [
    re_path(rf'^{settings.MEDIA_URL.lstrip("/")}(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
    path('check_media/', check_media),
]
