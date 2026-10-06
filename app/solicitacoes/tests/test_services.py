import pytest

from app.core.exceptions import SolicitacaoNaoEditavel, TransicaoInvalida
from app.solicitacoes import services
from app.solicitacoes.models import Categoria, HistoricoStatus, Solicitacao

pytestmark = pytest.mark.django_db

Status = Solicitacao.Status

TRANSICOES_INVALIDAS = [
    (Status.ABERTO, Status.CONCLUIDO),
    (Status.ABERTO, Status.ABERTO),
    (Status.EM_ATENDIMENTO, Status.ABERTO),
    (Status.EM_ATENDIMENTO, Status.EM_ATENDIMENTO),
    (Status.CONCLUIDO, Status.ABERTO),
    (Status.CONCLUIDO, Status.EM_ATENDIMENTO),
    (Status.CONCLUIDO, Status.CONCLUIDO),
]


# --- criação (RN02) ---

def test_criar_solicitacao_nasce_aberta_e_com_o_solicitante(colaborador, categoria_ti):
    solicitacao = services.criar_solicitacao(
        solicitante=colaborador,
        titulo='Mouse quebrado',
        descricao='O mouse parou de funcionar.',
        categoria=categoria_ti,
    )

    assert solicitacao.pk is not None
    assert solicitacao.status == Status.ABERTO
    assert solicitacao.solicitante == colaborador
    assert solicitacao.criado_em is not None


# --- edição (RN03) ---

def test_editar_solicitacao_aberta_altera_os_campos(solicitacao):
    outra_categoria = Categoria.objects.get(nome='RH')

    editada = services.editar_solicitacao(
        solicitacao, titulo='Novo título', categoria=outra_categoria
    )

    editada.refresh_from_db()
    assert editada.titulo == 'Novo título'
    assert editada.categoria == outra_categoria
    assert editada.descricao == 'Descrição de teste.'  # não enviada, não muda


def test_editar_solicitacao_atualiza_atualizado_em(solicitacao):
    antes = solicitacao.atualizado_em

    editada = services.editar_solicitacao(solicitacao, titulo='Outro título')

    assert editada.atualizado_em > antes


@pytest.mark.parametrize('status', [Status.EM_ATENDIMENTO, Status.CONCLUIDO])
def test_nao_edita_solicitacao_fora_de_aberto(fabrica_de_solicitacao, colaborador, status):
    solicitacao = fabrica_de_solicitacao(colaborador, status=status)

    with pytest.raises(SolicitacaoNaoEditavel):
        services.editar_solicitacao(solicitacao, titulo='Tentativa')

    solicitacao.refresh_from_db()
    assert solicitacao.titulo != 'Tentativa'


# --- exclusão (RN03) ---

def test_excluir_solicitacao_aberta_remove_do_banco(solicitacao):
    services.excluir_solicitacao(solicitacao)

    assert not Solicitacao.objects.filter(pk=solicitacao.pk).exists()


@pytest.mark.parametrize('status', [Status.EM_ATENDIMENTO, Status.CONCLUIDO])
def test_nao_exclui_solicitacao_fora_de_aberto(fabrica_de_solicitacao, colaborador, status):
    solicitacao = fabrica_de_solicitacao(colaborador, status=status)

    with pytest.raises(SolicitacaoNaoEditavel):
        services.excluir_solicitacao(solicitacao)

    assert Solicitacao.objects.filter(pk=solicitacao.pk).exists()


# --- alteração de status (RN07 e RN08) ---

def test_alterar_status_de_aberto_para_em_atendimento_grava_historico(solicitacao, atendente):
    atualizada = services.alterar_status(
        solicitacao, novo_status=Status.EM_ATENDIMENTO, usuario=atendente
    )

    assert atualizada.status == Status.EM_ATENDIMENTO
    registro = HistoricoStatus.objects.get(solicitacao=solicitacao)
    assert registro.status_anterior == Status.ABERTO
    assert registro.status_novo == Status.EM_ATENDIMENTO
    assert registro.alterado_por == atendente


def test_fluxo_completo_gera_dois_registros_em_ordem(solicitacao, atendente):
    services.alterar_status(solicitacao, novo_status=Status.EM_ATENDIMENTO, usuario=atendente)
    services.alterar_status(solicitacao, novo_status=Status.CONCLUIDO, usuario=atendente)

    pares = [(r.status_anterior, r.status_novo) for r in solicitacao.historico.all()]
    assert pares == [
        (Status.ABERTO, Status.EM_ATENDIMENTO),
        (Status.EM_ATENDIMENTO, Status.CONCLUIDO),
    ]


@pytest.mark.parametrize('origem, destino', TRANSICOES_INVALIDAS)
def test_transicao_invalida_e_rejeitada_sem_efeitos(
    fabrica_de_solicitacao, colaborador, atendente, origem, destino
):
    solicitacao = fabrica_de_solicitacao(colaborador, status=origem)

    with pytest.raises(TransicaoInvalida):
        services.alterar_status(solicitacao, novo_status=destino, usuario=atendente)

    solicitacao.refresh_from_db()
    assert solicitacao.status == origem
    assert not HistoricoStatus.objects.filter(solicitacao=solicitacao).exists()


def test_mensagem_da_transicao_invalida_cita_os_rotulos(
    fabrica_de_solicitacao, colaborador, atendente
):
    solicitacao = fabrica_de_solicitacao(colaborador, status=Status.CONCLUIDO)

    with pytest.raises(TransicaoInvalida) as erro:
        services.alterar_status(solicitacao, novo_status=Status.ABERTO, usuario=atendente)

    assert erro.value.mensagem == 'Não é possível alterar o status de Concluído para Aberto.'


def test_status_desconhecido_e_tratado_como_transicao_invalida(solicitacao, atendente):
    with pytest.raises(TransicaoInvalida):
        services.alterar_status(solicitacao, novo_status='XYZ', usuario=atendente)


def test_falha_ao_gravar_historico_desfaz_a_mudanca_de_status(
    solicitacao, atendente, monkeypatch
):
    def historico_com_defeito(*args, **kwargs):
        raise RuntimeError('falha simulada')

    monkeypatch.setattr(HistoricoStatus.objects, 'create', historico_com_defeito)

    with pytest.raises(RuntimeError):
        services.alterar_status(solicitacao, novo_status=Status.EM_ATENDIMENTO, usuario=atendente)

    solicitacao.refresh_from_db()
    assert solicitacao.status == Status.ABERTO