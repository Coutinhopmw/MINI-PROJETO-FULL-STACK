from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.core.permissions import EhAtendente, EhSolicitante
from app.solicitacoes import selectors, services
from app.solicitacoes.models import Solicitacao

from .filters import FiltroDeSolicitacao
from .serializers import (
    AlterarStatusSerializer,
    CategoriaSerializer,
    DashboardSerializer,
    HistoricoStatusSerializer,
    SolicitacaoDetalheSerializer,
    SolicitacaoEscritaSerializer,
    SolicitacaoListaSerializer,
)


class SolicitacaoViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']  # sem PUT
    filterset_class = FiltroDeSolicitacao

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # geração do schema
            return Solicitacao.objects.none()
        return selectors.solicitacoes_visiveis(self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return SolicitacaoListaSerializer
        if self.action in ('create', 'partial_update'):
            return SolicitacaoEscritaSerializer
        if self.action == 'alterar_status':
            return AlterarStatusSerializer
        return SolicitacaoDetalheSerializer

    def get_permissions(self):
        if self.action in ('partial_update', 'destroy'):
            return [IsAuthenticated(), EhSolicitante()]
        if self.action == 'alterar_status':
            return [IsAuthenticated(), EhAtendente()]
        return [IsAuthenticated()]

    def _resposta_detalhada(self, solicitacao, status_http=status.HTTP_200_OK):
        serializador = SolicitacaoDetalheSerializer(
            solicitacao, context=self.get_serializer_context()
        )
        return Response(serializador.data, status=status_http)

    @extend_schema(request=SolicitacaoEscritaSerializer, responses={201: SolicitacaoDetalheSerializer})
    def create(self, request, *args, **kwargs):
        serializador = self.get_serializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        solicitacao = services.criar_solicitacao(
            solicitante=request.user, **serializador.validated_data
        )
        return self._resposta_detalhada(solicitacao, status.HTTP_201_CREATED)

    @extend_schema(request=SolicitacaoEscritaSerializer, responses={200: SolicitacaoDetalheSerializer})
    def partial_update(self, request, *args, **kwargs):
        solicitacao = self.get_object()
        serializador = self.get_serializer(solicitacao, data=request.data, partial=True)
        serializador.is_valid(raise_exception=True)
        solicitacao = services.editar_solicitacao(solicitacao, **serializador.validated_data)
        return self._resposta_detalhada(solicitacao)

    def destroy(self, request, *args, **kwargs):
        services.excluir_solicitacao(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=AlterarStatusSerializer, responses={200: SolicitacaoDetalheSerializer})
    @action(detail=True, methods=['post'], url_path='status')
    def alterar_status(self, request, pk=None):
        solicitacao = self.get_object()
        serializador = self.get_serializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        solicitacao = services.alterar_status(
            solicitacao,
            novo_status=serializador.validated_data['status'],
            usuario=request.user,
        )
        return self._resposta_detalhada(solicitacao)

    @extend_schema(responses={200: HistoricoStatusSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='historico', pagination_class=None)
    def historico(self, request, pk=None):
        solicitacao = self.get_object()
        registros = selectors.historico_da_solicitacao(solicitacao)
        return Response(HistoricoStatusSerializer(registros, many=True).data)


class CategoriaListView(generics.ListAPIView):
    serializer_class = CategoriaSerializer
    pagination_class = None

    def get_queryset(self):
        return selectors.categorias_ativas()


class DashboardView(APIView):
    @extend_schema(responses={200: DashboardSerializer})
    def get(self, request):
        return Response(selectors.indicadores_do_dashboard(request.user))