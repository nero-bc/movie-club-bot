from django.urls import path

from . import views

urlpatterns = [
    path("", views.tennant_list, name="index"),
    path("t/<acct>", views.index, name="index"),
    path("u/<acct>", views.profile, name="profile"),
    path("status", views.status, name="status"),
    path("manifest.json", views.manifest, name="manifest"),
]
