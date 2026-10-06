import pytest
from django.http import Http404
from rest_framework import exceptions as excecoes_drf
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from app.core.exceptions import (
    SolicitacaoNaoEditavel,
    TransicaoInvalida,
    tratador_de_excecoes,
)


def corpo_do_erro(resposta):
    return resposta.data['erro']


def test_erro_de_dominio_devolve_409_com_codigo_proprio():
    resposta = tratador_de_excecoes(TransicaoInvalida('Não pode.'), {})

    assert resposta.status_code == 409
    assert corpo_do_erro(resposta)['codigo'] == 'TRANSICAO_INVALIDA'
    assert corpo_do_erro(resposta)['mensagem'] == 'Não pode.'


def test_solicitacao_nao_editavel_devolve_409():
    resposta = tratador_de_excecoes(SolicitacaoNaoEditavel(), {})

    assert resposta.status_code == 409
    assert corpo_do_erro(resposta)['codigo'] == 'SOLICITACAO_NAO_EDITAVEL'


def test_validacao_devolve_400_com_detalhes_por_campo():
    excecao = excecoes_drf.ValidationError({'titulo': ['Informe um título.']})

    resposta = tratador_de_excecoes(excecao, {})

    assert resposta.status_code == 400
    assert corpo_do_erro(resposta)['codigo'] == 'VALIDACAO'
    assert 'titulo' in corpo_do_erro(resposta)['detalhes']


def test_nao_autenticado_devolve_401_e_nao_403():
    resposta = tratador_de_excecoes(excecoes_drf.NotAuthenticated(), {})

    assert resposta.status_code == 401
    assert corpo_do_erro(resposta)['codigo'] == 'NAO_AUTENTICADO'


def test_permissao_negada_devolve_403():
    resposta = tratador_de_excecoes(excecoes_drf.PermissionDenied('Sem acesso.'), {})

    assert resposta.status_code == 403
    assert corpo_do_erro(resposta)['mensagem'] == 'Sem acesso.'


def test_http404_do_django_devolve_404_padronizado():
    resposta = tratador_de_excecoes(Http404(), {})

    assert resposta.status_code == 404
    assert corpo_do_erro(resposta)['codigo'] == 'NAO_ENCONTRADO'


def test_limite_excedido_devolve_429_com_retry_after():
    resposta = tratador_de_excecoes(excecoes_drf.Throttled(wait=30), {})

    assert resposta.status_code == 429
    assert corpo_do_erro(resposta)['codigo'] == 'LIMITE_EXCEDIDO'
    assert resposta['Retry-After'] == '30'


def test_erro_inesperado_nao_e_tratado():
    assert tratador_de_excecoes(RuntimeError('bug'), {}) is None


class VisaoProtegida(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return None


class VisaoComErroDeDominio(APIView):
    permission_classes = []

    def get(self, request):
        raise TransicaoInvalida()


def test_visao_sem_login_responde_401_no_formato_padrao():
    requisicao = APIRequestFactory().get('/')

    resposta = VisaoProtegida.as_view()(requisicao)

    assert resposta.status_code == 401
    assert corpo_do_erro(resposta)['codigo'] == 'NAO_AUTENTICADO'


def test_visao_que_levanta_erro_de_dominio_usa_o_tratador_configurado():
    requisicao = APIRequestFactory().get('/')

    resposta = VisaoComErroDeDominio.as_view()(requisicao)

    assert resposta.status_code == 409
    assert corpo_do_erro(resposta)['codigo'] == 'TRANSICAO_INVALIDA'