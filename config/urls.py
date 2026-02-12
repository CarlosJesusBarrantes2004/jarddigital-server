"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # 1. Panel de Administración (El clásico)
    path("admin/", admin.site.urls),

    # 2. LOGIN (Aquí es donde Postman pedirá el token)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 3. TUS NUEVAS APPS (Futuro)
    # Como ahora tienes apps separadas, en el futuro las agregaremos así:
    # path('api/users/', include('apps.users.urls')),
    # path('api/sales/', include('apps.sales.urls')),
    # ... por ahora las dejo comentadas para que no te den error si no has creado los archivos urls.py dentro de cada carpeta.
]
