from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        COLABORADOR = 'COLABORADOR', 'Colaborador'
        ATENDENTE = 'ATENDENTE', 'Atendente'

    perfil = models.CharField(
        max_length=20,
        choices=Perfil.choices,
        default=Perfil.COLABORADOR,
    )

    class Meta:
        db_table = 'usuario'
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(perfil__in=['COLABORADOR', 'ATENDENTE']),
                name='usuario_perfil_valido',
            ),
        ]

    @property
    def is_atendente(self):
        return self.perfil == self.Perfil.ATENDENTE

    def __str__(self):
        return self.get_full_name() or self.username