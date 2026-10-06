from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app.accounts.models import Usuario
from app.solicitacoes.models import Categoria, HistoricoStatus, Solicitacao

Status = Solicitacao.Status
CAMINHO_DE_STATUS = [Status.ABERTO, Status.EM_ATENDIMENTO, Status.CONCLUIDO]

# (username, nome, perfil, superusuario)
USUARIOS_DEMO = [
    ('colaborador', 'Carla Colaboradora', Usuario.Perfil.COLABORADOR, False),
    ('colaborador2', 'Caio Colaborador', Usuario.Perfil.COLABORADOR, False),
    ('atendente', 'Ana Atendente', Usuario.Perfil.ATENDENTE, False),
    ('admin', 'Administrador', Usuario.Perfil.ATENDENTE, True),
]

SENHA_DEMO = 'qwe123'

# (titulo, descricao, categoria, solicitante, status_final, dias_atras)
SOLICITACOES_DEMO = [
    ('Impressora do 2º andar sem toner', 'Trocar o toner da impressora.', 'TI', 'colaborador', Status.ABERTO, 1),
    ('Notebook não liga', 'Equipamento não inicializa desde ontem.', 'TI', 'colaborador2', Status.EM_ATENDIMENTO, 3),
    ('Acesso à VPN', 'Liberar acesso remoto para home office.', 'TI', 'colaborador', Status.CONCLUIDO, 20),
    ('Solicitação de férias', 'Agendar férias para janeiro.', 'RH', 'colaborador', Status.EM_ATENDIMENTO, 6),
    ('Atualização de dados cadastrais', 'Corrigir endereço no cadastro.', 'RH', 'colaborador2', Status.ABERTO, 2),
    ('Declaração de vínculo', 'Declaração para apresentar ao banco.', 'RH', 'colaborador2', Status.CONCLUIDO, 25),
    ('Compra de monitores', 'Dois monitores para a equipe.', 'Compras', 'colaborador2', Status.CONCLUIDO, 14),
    ('Material de escritório', 'Reposição de papel e canetas.', 'Compras', 'colaborador', Status.ABERTO, 0),
    ('Cadeira ergonômica', 'Cotação de cadeira para a mesa 12.', 'Compras', 'colaborador2', Status.EM_ATENDIMENTO, 8),
    ('Reembolso de viagem', 'Reembolso da viagem a São Paulo.', 'Financeiro', 'colaborador', Status.EM_ATENDIMENTO, 5),
    ('Segunda via de nota fiscal', 'Nota fiscal do fornecedor ABC.', 'Financeiro', 'colaborador2', Status.CONCLUIDO, 18),
    ('Adiantamento de despesas', 'Adiantamento para evento externo.', 'Financeiro', 'colaborador', Status.ABERTO, 4),
    ('Ar-condicionado com vazamento', 'Vazamento na sala de reuniões 3.', 'Infraestrutura', 'colaborador2', Status.EM_ATENDIMENTO, 7),
    ('Lâmpadas queimadas no corredor', 'Trocar lâmpadas do 1º andar.', 'Infraestrutura', 'colaborador', Status.CONCLUIDO, 30),
    ('Reserva da sala de treinamento', 'Reservar a sala para a próxima semana.', 'Infraestrutura', 'colaborador2', Status.ABERTO, 1),
]


class Command(BaseCommand):
    help = 'Cria usuários e solicitações de demonstração (idempotente).'

    @transaction.atomic
    def handle(self, *args, **opcoes):
        usuarios = self._criar_usuarios()
        self._criar_solicitacoes(usuarios)
        self.stdout.write(self.style.SUCCESS('Dados de demonstração prontos.'))

    def _criar_usuarios(self):
        usuarios = {}
        for username, nome, perfil, superusuario in USUARIOS_DEMO:
            usuario, criado = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nome,
                    'perfil': perfil,
                    'is_staff': superusuario,
                    'is_superuser': superusuario,
                },
            )
            if criado:
                usuario.set_password(SENHA_DEMO)
                usuario.save(update_fields=['password'])
            usuarios[username] = usuario
        return usuarios

    def _criar_solicitacoes(self, usuarios):
        atendente = usuarios['atendente']
        for titulo, descricao, nome_categoria, username, status_final, dias_atras in SOLICITACOES_DEMO:
            solicitacao, criada = Solicitacao.objects.get_or_create(
                titulo=titulo,
                solicitante=usuarios[username],
                defaults={
                    'descricao': descricao,
                    'categoria': Categoria.objects.get(nome=nome_categoria),
                },
            )
            if not criada:
                continue

            momento_criacao = timezone.now() - timedelta(days=dias_atras)
            Solicitacao.objects.filter(pk=solicitacao.pk).update(
                criado_em=momento_criacao,
                status=status_final,
            )
            self._registrar_historico(solicitacao, status_final, atendente, momento_criacao)

    def _registrar_historico(self, solicitacao, status_final, atendente, momento_criacao):
        posicao_final = CAMINHO_DE_STATUS.index(status_final)
        for posicao in range(1, posicao_final + 1):
            registro = HistoricoStatus.objects.create(
                solicitacao=solicitacao,
                status_anterior=CAMINHO_DE_STATUS[posicao - 1],
                status_novo=CAMINHO_DE_STATUS[posicao],
                alterado_por=atendente,
            )
            HistoricoStatus.objects.filter(pk=registro.pk).update(
                alterado_em=momento_criacao + timedelta(hours=4 * posicao),
            )