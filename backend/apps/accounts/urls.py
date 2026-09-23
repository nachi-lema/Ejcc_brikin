from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profil/', views.profil_view, name='profil'),
    path('utilisateurs/', views.utilisateurs_list, name='utilisateurs_list'),
    path('utilisateurs/nouveau/', views.utilisateur_create, name='utilisateur_create'),
    path('utilisateurs/<uuid:pk>/modifier/', views.utilisateur_update, name='utilisateur_update'),
    path('utilisateurs/<uuid:pk>/toggle/', views.utilisateur_toggle, name='utilisateur_toggle'),
]