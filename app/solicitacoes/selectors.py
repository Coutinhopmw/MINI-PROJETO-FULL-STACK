from django.db.models import Count, Q

from .models import Categoria, Solicitacao

Status = Solicitacao.Status


def solicitacoes_visiveis(usuario):
    """RN05: atendente vê todas; colaborador vê só as próprias."""
    consulta = Solicitacao.objects.select_related('categoria', 'solicitante')
    if usuario.eh_atendente:
        return consulta
    return consulta.filter(solicitante=usuario)


def indicadores_do_dashboard(usuario):
    return solicitacoes_visiveis(usuario).aggregate(
        total=Count('id'),
        abertas=Count('id', filter=Q(status=Status.ABERTO)),
        em_atendimento=Count('id', filter=Q(status=Status.EM_ATENDIMENTO)),
        concluidas=Count('id', filter=Q(status=Status.CONCLUIDO)),
    )


def historico_da_solicitacao(solicitacao):
    return solicitacao.historico.select_related('alterado_por')


def categorias_ativas():
    return Categoria.objects.filter(ativa=True)