from django.urls import path
from . import views

app_name = 'partenaires'

urlpatterns = [
    path('', views.liste, name='liste'),
    path('nouveau/', views.creer, name='creer'),
    path('<uuid:pk>/', views.detail, name='detail'),
    path('<uuid:pk>/modifier/', views.modifier, name='modifier'),
    path('<uuid:pk>/desactiver/', views.desactiver, name='desactiver'),
    path('<uuid:pk>/reactiver/', views.reactiver, name='reactiver'),
    path('<uuid:pk>/situation/', views.situation, name='situation'),
]