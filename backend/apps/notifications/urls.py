from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.liste, name='liste'),
    path('<uuid:pk>/lu/', views.marquer_lu, name='marquer_lu'),
    path('tout-lu/', views.tout_marquer_lu, name='tout_marquer_lu'),
]