from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.solicitacoes.models import Categoria, Solicitacao

pytestmark = pytest.mark.django_db

URL = '/api/v1/solicitacoes/'
FUSO = ZoneInfo('America/Sao_Paulo')
Status = Solicitacao.Status


def em_outubro(dia):
    return datetime(2026, 10, dia, 12, 0, tzinfo=FUSO)


@pytest.fixture
def massa_de_dados(fabrica_de_solicitacao, atendente, colaborador):
    """Quatro solicitações em datas, categorias e status diferentes."""
    ti, rh = Categoria.objects.get(nome='TI'), Categoria.objects.get(nome='RH')
    definicoes = [
        ('Impressora sem toner', ti, Status.ABERTO, 1),
        ('Férias de janeiro', rh, Status.EM_ATENDIMENTO, 3),
        ('Notebook não liga', ti, Status.CONCLUIDO, 5),
        ('Acesso ao sistema', rh, Status.ABERTO, 7),
    ]
    for titulo, categoria, status, dia in definicoes:
        solicitacao = fabrica_de_solicitacao(colaborador, titulo=titulo, categoria=categoria, status=status)
        Solicitacao.objects.filter(pk=solicitacao.pk).update(criado_em=em_outubro(dia))


def titulos(resposta):
    assert resposta.status_code == 200
    return {item['titulo'] for item in resposta.json()['results']}


def test_filtra_por_status(cliente_do_atendente, massa_de_dados):
    assert titulos(cliente_do_atendente.get(URL, {'status': 'ABERTO'})) == {
        'Impressora sem toner', 'Acesso ao sistema',
    }


def test_filtra_por_categoria(cliente_do_atendente, massa_de_dados):
    rh = Categoria.objects.get(nome='RH')

    assert titulos(cliente_do_atendente.get(URL, {'categoria': rh.pk})) == {
        'Férias de janeiro', 'Acesso ao sistema',
    }


def test_filtra_por_texto_sem_diferenciar_maiusculas(cliente_do_atendente, massa_de_dados):
    assert titulos(cliente_do_atendente.get(URL, {'q': 'IMPRESSORA'})) == {'Impressora sem toner'}


def test_periodo_inclui_o_primeiro_e_o_ultimo_dia(cliente_do_atendente, massa_de_dados):
    resposta = cliente_do_atendente.get(URL, {'data_inicio': '2026-10-03', 'data_fim': '2026-10-05'})

    assert titulos(resposta) == {'Férias de janeiro', 'Notebook não liga'}


def test_periodo_de_um_unico_dia(cliente_do_atendente, massa_de_dados):
    resposta = cliente_do_atendente.get(URL, {'data_inicio': '2026-10-07', 'data_fim': '2026-10-07'})

    assert titulos(resposta) == {'Acesso ao sistema'}


def test_filtros_se_combinam(cliente_do_atendente, massa_de_dados):
    ti = Categoria.objects.get(nome='TI')
    resposta = cliente_do_atendente.get(URL, {'categoria': ti.pk, 'status': 'CONCLUIDO', 'data_inicio': '2026-10-01'})

    assert titulos(resposta) == {'Notebook não liga'}


def test_filtros_respeitam_o_escopo_do_perfil(
    cliente_do_outro_colaborador, massa_de_dados
):
    assert titulos(cliente_do_outro_colaborador.get(URL, {'status': 'ABERTO'})) == set()


def test_periodo_invertido_devolve_400(cliente_do_atendente, massa_de_dados):
    resposta = cliente_do_atendente.get(URL, {'data_inicio': '2026-10-09', 'data_fim': '2026-10-01'})

    assert resposta.status_code == 400
    assert resposta.json()['erro']['codigo'] == 'VALIDACAO'


@pytest.mark.parametrize('parametros', [
    {'status': 'XYZ'},
    {'categoria': 99999},
    {'data_inicio': 'ontem'},
])
def test_valores_invalidos_devolvem_400(cliente_do_atendente, massa_de_dados, parametros):
    assert cliente_do_atendente.get(URL, parametros).status_code == 400