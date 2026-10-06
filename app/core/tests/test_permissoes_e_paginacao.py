from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser

from app.accounts.models import Usuario
from app.core.pagination import PaginacaoPadrao
from app.core.permissions import EhAtendente, EhSolicitante


def requisicao_de(usuario):
    return SimpleNamespace(user=usuario)


def test_atendente_tem_permissao_de_atendente():
    usuario = Usuario(id=1, perfil=Usuario.Perfil.ATENDENTE)

    assert EhAtendente().has_permission(requisicao_de(usuario), None) is True


def test_colaborador_nao_tem_permissao_de_atendente():
    usuario = Usuario(id=2, perfil=Usuario.Perfil.COLABORADOR)

    assert EhAtendente().has_permission(requisicao_de(usuario), None) is False


def test_anonimo_nao_tem_permissao_de_atendente():
    assert EhAtendente().has_permission(requisicao_de(AnonymousUser()), None) is False


def test_somente_o_dono_passa_na_permissao_de_solicitante():
    dono = Usuario(id=1)
    outro = Usuario(id=2)
    solicitacao = SimpleNamespace(solicitante_id=1)
    permissao = EhSolicitante()

    assert permissao.has_object_permission(requisicao_de(dono), None, solicitacao) is True
    assert permissao.has_object_permission(requisicao_de(outro), None, solicitacao) is False


def test_paginacao_padrao_tem_dez_itens_por_pagina():
    assert PaginacaoPadrao.page_size == 10