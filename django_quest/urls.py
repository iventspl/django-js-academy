from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Django Quest studio"
admin.site.site_title = "Django Quest studio"
admin.site.index_title = "Content & learner data"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("js/", include("js_academy.urls")),
    path("ai/", include("ai_academy.urls")),
    path("", include("dojo.urls")),
]
