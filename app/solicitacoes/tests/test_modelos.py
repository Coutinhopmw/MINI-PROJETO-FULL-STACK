from io import StringIO

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from app.accounts.models import Usuario
from app.solicitacoes.management.commands.seed_demo import SOLICITACOES_DEMO
from app.solicitacoes.models import Categoria, HistoricoStatus, Solicitacao

pytestmark = pytest.mark.django_db

CATEGORIAS_INICIAIS = {'TI', 'RH', 'Compras', 'Financeiro', 'Infraestrutura'}


@pytest.fixture
def categoria_ti():
    return Categoria.objects.get(nome='TI')


@pytest.fixture
def colaborador():
    return Usuario.objects.create_user(username='carla', password='senha-de-teste-1')


@pytest.fixture
def atendente():
    return Usuario.objects.create_user(
        username='ana',
        password='senha-de-teste-2',
        perfil=Usuario.Perfil.ATENDENTE,
    )


@pytest.fixture
def solicitacao(colaborador, categoria_ti):
    return Solicitacao.objects.create(
        titulo='Impressora sem toner',
        descricao='Trocar o toner da impressora do 2º andar.',
        categoria=categoria_ti,
        solicitante=colaborador,
    )


def executar_seed():
    call_command('seed_demo', stdout=StringIO())


def test_categorias_iniciais_existem():
    nomes = set(Categoria.objects.values_list('nome', flat=True))

    assert CATEGORIAS_INICIAIS <= nomes


def test_categorias_iniciais_nascem_ativas():
    categorias = Categoria.objects.filter(nome__in=CATEGORIAS_INICIAIS)

    assert categorias.count() == len(CATEGORIAS_INICIAIS)
    assert all(categoria.ativa for categoria in categorias)


def test_solicitacao_nasce_aberta_com_data_de_criacao(solicitacao):
    assert solicitacao.status == Solicitacao.Status.ABERTO
    assert solicitacao.criado_em is not None
    assert solicitacao.atualizado_em is not None


def test_codigo_da_solicitacao_e_derivado_do_id(solicitacao):
    assert solicitacao.codigo == f'SOL-{solicitacao.pk:06d}'


def test_codigo_formata_com_seis_digitos():
    assert Solicitacao(pk=42).codigo == 'SOL-000042'


def test_codigo_e_nulo_para_solicitacao_nao_salva():
    assert Solicitacao().codigo is None


def test_banco_rejeita_status_invalido_na_solicitacao(colaborador, categoria_ti):
    with pytest.raises(IntegrityError), transaction.atomic():
        Solicitacao.objects.create(
            titulo='Status inválido',
            descricao='Não deveria ser gravada.',
            categoria=categoria_ti,
            solicitante=colaborador,
            status='XYZ',
        )


def test_banco_rejeita_historico_sem_mudanca_de_status(solicitacao, atendente):
    with pytest.raises(IntegrityError), transaction.atomic():
        HistoricoStatus.objects.create(
            solicitacao=solicitacao,
            status_anterior=Solicitacao.Status.ABERTO,
            status_novo=Solicitacao.Status.ABERTO,
            alterado_por=atendente,
        )


def test_categoria_com_solicitacao_nao_pode_ser_excluida(solicitacao, categoria_ti):
    with pytest.raises(ProtectedError):
        categoria_ti.delete()


def test_usuario_com_solicitacao_nao_pode_ser_excluido(solicitacao, colaborador):
    with pytest.raises(ProtectedError):
        colaborador.delete()


def test_excluir_solicitacao_apaga_o_historico(solicitacao, atendente):
    HistoricoStatus.objects.create(
        solicitacao=solicitacao,
        status_anterior=Solicitacao.Status.ABERTO,
        status_novo=Solicitacao.Status.EM_ATENDIMENTO,
        alterado_por=atendente,
    )

    solicitacao.delete()

    assert HistoricoStatus.objects.count() == 0


def test_historico_e_listado_na_ordem_das_alteracoes(solicitacao, atendente):
    for anterior, novo in [
        (Solicitacao.Status.ABERTO, Solicitacao.Status.EM_ATENDIMENTO),
        (Solicitacao.Status.EM_ATENDIMENTO, Solicitacao.Status.CONCLUIDO),
    ]:
        HistoricoStatus.objects.create(
            solicitacao=solicitacao,
            status_anterior=anterior,
            status_novo=novo,
            alterado_por=atendente,
        )

    novos_status = [registro.status_novo for registro in solicitacao.historico.all()]

    assert novos_status == [Solicitacao.Status.EM_ATENDIMENTO, Solicitacao.Status.CONCLUIDO]


def test_seed_demo_cria_os_dados_esperados():
    executar_seed()

    assert Usuario.objects.count() == 4
    assert Solicitacao.objects.count() == len(SOLICITACOES_DEMO)
    assert Usuario.objects.get(username='admin').is_superuser


def test_seed_demo_nao_duplica_dados_ao_rodar_duas_vezes():
    executar_seed()
    usuarios = Usuario.objects.count()
    solicitacoes = Solicitacao.objects.count()
    historicos = HistoricoStatus.objects.count()

    executar_seed()

    assert Usuario.objects.count() == usuarios
    assert Solicitacao.objects.count() == solicitacoes
    assert HistoricoStatus.objects.count() == historicos


def test_seed_demo_gera_historico_coerente_com_o_status():
    executar_seed()
    registros_esperados = {
        Solicitacao.Status.ABERTO: 0,
        Solicitacao.Status.EM_ATENDIMENTO: 1,
        Solicitacao.Status.CONCLUIDO: 2,
    }

    for solicitacao in Solicitacao.objects.all():
        assert solicitacao.historico.count() == registros_esperados[solicitacao.status]
