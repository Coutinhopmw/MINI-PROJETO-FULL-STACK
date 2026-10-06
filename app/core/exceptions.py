from django.core.exceptions import PermissionDenied as PermissaoNegadaDjango
from django.http import Http404
from rest_framework import exceptions as excecoes_drf
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as tratador_padrao


class ErroDeDominio(Exception):
    """Base das violações de regra de negócio. Não conhece HTTP além do status."""

    codigo = 'ERRO_DE_DOMINIO'
    status_http = status.HTTP_400_BAD_REQUEST
    mensagem_padrao = 'Operação inválida.'

    def __init__(self, mensagem=None, detalhes=None):
        self.mensagem = mensagem or self.mensagem_padrao
        self.detalhes = detalhes or {}
        super().__init__(self.mensagem)


class SolicitacaoNaoEditavel(ErroDeDominio):
    codigo = 'SOLICITACAO_NAO_EDITAVEL'
    status_http = status.HTTP_409_CONFLICT
    mensagem_padrao = 'Só é possível editar ou excluir solicitações com status Aberto.'


class TransicaoInvalida(ErroDeDominio):
    codigo = 'TRANSICAO_INVALIDA'
    status_http = status.HTTP_409_CONFLICT
    mensagem_padrao = 'Transição de status não permitida.'


# (classe da exceção, status HTTP, código, mensagem padrão)
MAPA_DE_ERROS = [
    (excecoes_drf.ValidationError, 400, 'VALIDACAO', 'Dados inválidos.'),
    (excecoes_drf.ParseError, 400, 'REQUISICAO_INVALIDA', 'Requisição malformada.'),
    (excecoes_drf.NotAuthenticated, 401, 'NAO_AUTENTICADO', 'Autenticação necessária.'),
    (excecoes_drf.AuthenticationFailed, 401, 'NAO_AUTENTICADO', 'Credenciais inválidas.'),
    (excecoes_drf.PermissionDenied, 403, 'SEM_PERMISSAO', None),
    (excecoes_drf.NotFound, 404, 'NAO_ENCONTRADO', 'Recurso não encontrado.'),
    (excecoes_drf.MethodNotAllowed, 405, 'METODO_NAO_PERMITIDO', 'Método não permitido.'),
    (excecoes_drf.Throttled, 429, 'LIMITE_EXCEDIDO', 'Muitas tentativas. Tente novamente em instantes.'),
]


def montar_resposta_de_erro(codigo, mensagem, status_http, detalhes=None, cabecalhos=None):
    corpo = {'erro': {'codigo': codigo, 'mensagem': mensagem, 'detalhes': detalhes or {}}}
    return Response(corpo, status=status_http, headers=cabecalhos)


def tratador_de_excecoes(excecao, contexto):
    if isinstance(excecao, ErroDeDominio):
        return montar_resposta_de_erro(
            excecao.codigo, excecao.mensagem, excecao.status_http, excecao.detalhes
        )

    # O DRF converte estas duas internamente, mas devolve a original para nós.
    if isinstance(excecao, Http404):
        excecao = excecoes_drf.NotFound()
    elif isinstance(excecao, PermissaoNegadaDjango):
        excecao = excecoes_drf.PermissionDenied()

    resposta_padrao = tratador_padrao(excecao, contexto)
    if resposta_padrao is None:
        return None  # erro inesperado: deixa o Django devolver o 500

    cabecalhos = {}
    if 'Retry-After' in resposta_padrao:
        cabecalhos['Retry-After'] = resposta_padrao['Retry-After']

    for classe, status_http, codigo, mensagem in MAPA_DE_ERROS:
        if isinstance(excecao, classe):
            if isinstance(excecao, excecoes_drf.ValidationError):
                detalhes = excecao.detail if isinstance(excecao.detail, dict) else {'geral': excecao.detail}
                return montar_resposta_de_erro(codigo, mensagem, status_http, detalhes, cabecalhos)
            if mensagem is None:  # PermissionDenied: usa o `message` da permissão
                mensagem = str(excecao.detail)
            return montar_resposta_de_erro(codigo, mensagem, status_http, cabecalhos=cabecalhos)

    # Qualquer outra APIException (ex.: 415, 406): mantém o status que o DRF decidiu.
    return montar_resposta_de_erro(
        str(getattr(excecao, 'default_code', 'ERRO')).upper(),
        str(excecao.detail),
        resposta_padrao.status_code,
        cabecalhos=cabecalhos,
    )