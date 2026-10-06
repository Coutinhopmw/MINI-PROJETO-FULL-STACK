from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CategoriaListView, DashboardView, SolicitacaoViewSet

roteador = SimpleRouter()
roteador.register('solicitacoes', SolicitacaoViewSet, basename='solicitacao')

urlpatterns = [
    path('categorias/', CategoriaListView.as_view(), name='api_categorias'),
    path('dashboard/', DashboardView.as_view(), name='api_dashboard'),
    *roteador.urls,
]