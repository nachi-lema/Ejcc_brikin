from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('paiements/', views.paiements_liste, name='paiements_liste'),
    path('paiements/nouveau/', views.paiement_create, name='paiement_create'),
    path('paiements/<uuid:pk>/', views.paiement_detail, name='paiement_detail'),
    path('paiements/<uuid:pk>/annuler/', views.paiement_annuler, name='paiement_annuler'),
    path('situation/', views.situation_financiere, name='situation_financiere'),
]