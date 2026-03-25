from django.contrib import admin
from django.urls import include, path

from config.docs import schema_view, swagger_ui_view

admin.site.site_header = "Администрирование парикмахерской"
admin.site.site_title = "Панель администратора"
admin.site.index_title = "Управление системой"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", schema_view, name="openapi-schema"),
    path("api/docs/", swagger_ui_view, name="swagger-ui"),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.salon.urls")),
]
