from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('u/<acct>', views.profile, name='profile'),
]
