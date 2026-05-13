from django.urls import path

from . import views

app_name = "campaigns"

urlpatterns = [
    path("", views.campaign_list, name="list"),
    path("new/", views.campaign_create, name="create"),
    path("<int:pk>/", views.campaign_detail, name="detail"),
    path("<int:pk>/manage/", views.campaign_manage, name="manage"),
    path("<int:pk>/recipients/", views.campaign_recipients_json, name="recipients_json"),
    path("<int:pk>/export/", views.campaign_recipients_export, name="recipients_export"),
    path("<int:pk>/delete/", views.campaign_delete, name="delete"),
    # Helpers used by the create form
    path("templates/preview/", views.template_preview, name="template_preview"),
    path("templates/normalise/", views.template_normalise, name="template_normalise"),
    path("templates/save/", views.template_save, name="template_save"),
    path("templates/<int:pk>/", views.template_get, name="template_get"),
]
