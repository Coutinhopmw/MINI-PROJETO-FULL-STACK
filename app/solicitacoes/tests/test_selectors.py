import pytest

from app.solicitacoes import selectors
from app.solicitacoes.models import Categoria, HistoricoStatus, Solicitacao

pytestmark = pytest.mark.django_db

Status = Solicitacao.Status


def test_colaborador_ve_apenas_as_proprias_solicitacoes(
    fabrica_de_solicitacao, colaborador, outro_colaborador
):
    propria = fabrica_de_solicitacao(colaborador)
    fabrica_de_solicitacao(outro_colaborador)

    assert list(selectors.solicitacoes_visiveis(colaborador)) == [propria]


def test_atendente_ve_todas_as_solicitacoes(
    fabrica_de_solicitacao, colaborador, outro_colaborador, atendente
):
    fabrica_de_solicitacao(colaborador)
    fabrica_de_solicitacao(outro_colaborador)

    assert selectors.solicitacoes_visiveis(atendente).count() == 2


def test_listagem_nao_gera_consultas_extras_por_linha(
    fabrica_de_solicitacao, colaborador, atendente, django_assert_num_queries
):
    for _ in range(3):
        fabrica_de_solicitacao(colaborador)

    with django_assert_num_queries(1):
        for solicitacao in selectors.solicitacoes_visiveis(atendente):
            solicitacao.categoria.nome
            solicitacao.solicitante.username


def test_indicadores_do_atendente_somam_todas_as_solicitacoes(
    fabrica_de_solicitacao, colaborador, outro_colaborador, atendente
):
    fabrica_de_solicitacao(colaborador, status=Status.ABERTO)
    fabrica_de_solicitacao(colaborador, status=Status.EM_ATENDIMENTO)
    fabrica_de_solicitacao(outro_colaborador, status=Status.CONCLUIDO)
    fabrica_de_solicitacao(outro_colaborador, status=Status.CONCLUIDO)

    assert selectors.indicadores_do_dashboard(atendente) == {
        'total': 4, 'abertas': 1, 'em_atendimento': 1, 'concluidas': 2,
    }


def test_indicadores_do_colaborador_respeitam_o_escopo(
    fabrica_de_solicitacao, colaborador, outro_colaborador
):
    fabrica_de_solicitacao(colaborador, status=Status.ABERTO)
    fabrica_de_solicitacao(outro_colaborador, status=Status.CONCLUIDO)

    assert selectors.indicadores_do_dashboard(colaborador) == {
        'total': 1, 'abertas': 1, 'em_atendimento': 0, 'concluidas': 0,
    }


def test_indicadores_sem_solicitacoes_sao_zero(colaborador):
    assert selectors.indicadores_do_dashboard(colaborador) == {
        'total': 0, 'abertas': 0, 'em_atendimento': 0, 'concluidas': 0,
    }


def test_historico_vem_em_ordem_com_o_autor_carregado(
    solicitacao, atendente, django_assert_num_queries
):
    HistoricoStatus.objects.create(
        solicitacao=solicitacao, status_anterior=Status.ABERTO,
        status_novo=Status.EM_ATENDIMENTO, alterado_por=atendente,
    )

    with django_assert_num_queries(1):
        registros = list(selectors.historico_da_solicitacao(solicitacao))
        assert registros[0].alterado_por.username == 'ana'


def test_categorias_ativas_ignora_as_desativadas():
    Categoria.objects.filter(nome='RH').update(ativa=False)

    nomes = set(selectors.categorias_ativas().values_list('nome', flat=True))

    assert 'RH' not in nomes
    assert 'TI' in nomes