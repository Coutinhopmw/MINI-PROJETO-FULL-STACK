from django.conf import settings
from django.db import models


class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        db_table = 'categoria'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Solicitacao(models.Model):
    class Status(models.TextChoices):
        ABERTO = 'ABERTO', 'Aberto'
        EM_ATENDIMENTO = 'EM_ATENDIMENTO', 'Em atendimento'
        CONCLUIDO = 'CONCLUIDO', 'Concluído'

    titulo = models.CharField(max_length=150)
    descricao = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABERTO,
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='solicitacoes',
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='solicitacoes',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'solicitacao'
        verbose_name = 'solicitação'
        verbose_name_plural = 'solicitações'
        ordering = ['-criado_em', '-id']
        indexes = [
            models.Index(fields=['status'], name='solicitacao_status_idx'),
            models.Index(fields=['criado_em'], name='solicitacao_criado_em_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=['ABERTO', 'EM_ATENDIMENTO', 'CONCLUIDO'],
                ),
                name='solicitacao_status_valido',
            ),
        ]

    @property
    def codigo(self):
        if self.pk is None:
            return None
        return f'SOL-{self.pk:06d}'

    def __str__(self):
        return f'{self.codigo} - {self.titulo}'


class HistoricoStatus(models.Model):
    solicitacao = models.ForeignKey(
        Solicitacao,
        on_delete=models.CASCADE,
        related_name='historico',
    )
    status_anterior = models.CharField(
        max_length=20,
        choices=Solicitacao.Status.choices,
    )
    status_novo = models.CharField(
        max_length=20,
        choices=Solicitacao.Status.choices,
    )
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='alteracoes_de_status',
    )
    alterado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historico_status'
        verbose_name = 'histórico de status'
        verbose_name_plural = 'históricos de status'
        ordering = ['alterado_em', 'id']
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(status_anterior=models.F('status_novo')),
                name='historico_status_mudou',
            ),
        ]

    def __str__(self):
        return f'{self.solicitacao.codigo}: {self.status_anterior} -> {self.status_novo}'