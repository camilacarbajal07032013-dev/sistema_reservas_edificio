from django.contrib import admin
from django.urls import path, include
from reservas.views import setup_admin_user

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reservas.urls')),
    path('setup-admin-xyz/', setup_admin_user),
]