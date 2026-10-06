from django.db import transaction

from app.core.exceptions import SolicitacaoNaoEditavel, TransicaoInvalida

from .models import HistoricoStatus, Solicitacao

Status = Solicitacao.Status

TRANSICOES_PERMITIDAS = {
    Status.ABERTO: {Status.EM_ATENDIMENTO},
    Status.EM_ATENDIMENTO: {Status.CONCLUIDO},
    Status.CONCLUIDO: set(),
}


def _rotulo_do_status(valor):
    try:
        return Status(valor).label
    except ValueError:
        return str(valor)


def _bloquear(solicitacao):
    """Relê a solicitação com bloqueio de linha, para decidir sobre o estado mais recente."""
    return Solicitacao.objects.select_for_update().get(pk=solicitacao.pk)


def _garantir_editavel(solicitacao):
    if solicitacao.status != Status.ABERTO:
        raise SolicitacaoNaoEditavel()


@transaction.atomic
def criar_solicitacao(*, solicitante, titulo, descricao, categoria):
    # RN02: status, data e solicitante nunca vêm do cliente.
    return Solicitacao.objects.create(
        solicitante=solicitante,
        titulo=titulo,
        descricao=descricao,
        categoria=categoria,
    )


@transaction.atomic
def editar_solicitacao(solicitacao, *, titulo=None, descricao=None, categoria=None):
    solicitacao = _bloquear(solicitacao)
    _garantir_editavel(solicitacao)  # RN03

    novos_valores = {'titulo': titulo, 'descricao': descricao, 'categoria': categoria}
    campos_alterados = [campo for campo, valor in novos_valores.items() if valor is not None]
    for campo in campos_alterados:
        setattr(solicitacao, campo, novos_valores[campo])

    solicitacao.save(update_fields=[*campos_alterados, 'atualizado_em'])
    return solicitacao


@transaction.atomic
def excluir_solicitacao(solicitacao):
    solicitacao = _bloquear(solicitacao)
    _garantir_editavel(solicitacao)  # RN03
    solicitacao.delete()


@transaction.atomic
def alterar_status(solicitacao, *, novo_status, usuario):
    solicitacao = _bloquear(solicitacao)
    status_anterior = solicitacao.status

    if novo_status not in TRANSICOES_PERMITIDAS.get(status_anterior, set()):  # RN07
        raise TransicaoInvalida(
            f'Não é possível alterar o status de {_rotulo_do_status(status_anterior)} '
            f'para {_rotulo_do_status(novo_status)}.'
        )

    solicitacao.status = novo_status
    solicitacao.save(update_fields=['status', 'atualizado_em'])

    HistoricoStatus.objects.create(  # RN08: mesma transação da mudança
        solicitacao=solicitacao,
        status_anterior=status_anterior,
        status_novo=novo_status,
        alterado_por=usuario,
    )
    return solicitacao