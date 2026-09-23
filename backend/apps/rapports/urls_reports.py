from django.urls import path
from . import views

app_name = 'rapports_reports'

urlpatterns = [
    path('mensuel/', views.rapport_mensuel, name='mensuel'),
    path('trimestriel/', views.rapport_trimestriel, name='trimestriel'),
    path('annuel/', views.rapport_annuel, name='annuel'),
    path('partenaire/<uuid:pk>/', views.rapport_partenaire, name='partenaire'),
]