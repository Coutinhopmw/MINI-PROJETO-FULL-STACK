from rest_framework import serializers

from app.accounts.api.serializers import UsuarioResumoSerializer
from app.solicitacoes import services
from app.solicitacoes.models import Categoria, HistoricoStatus, Solicitacao


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ('id', 'nome')


class SolicitacaoListaSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    solicitante = UsuarioResumoSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Solicitacao
        fields = (
            'id', 'codigo', 'titulo', 'categoria', 'solicitante',
            'status', 'status_display', 'criado_em',
        )


class SolicitacaoDetalheSerializer(SolicitacaoListaSerializer):
    pode_editar = serializers.SerializerMethodField()
    proximos_status = serializers.SerializerMethodField()

    class Meta(SolicitacaoListaSerializer.Meta):
        fields = SolicitacaoListaSerializer.Meta.fields + (
            'descricao', 'atualizado_em', 'pode_editar', 'proximos_status',
        )

    def get_pode_editar(self, solicitacao) -> bool:
        usuario = self.context['request'].user
        return (
            solicitacao.status == Solicitacao.Status.ABERTO
            and solicitacao.solicitante_id == usuario.id
        )

    def get_proximos_status(self, solicitacao) -> list[str]:
        usuario = self.context['request'].user
        if not usuario.eh_atendente:
            return []
        permitidos = services.TRANSICOES_PERMITIDAS.get(solicitacao.status, set())
        return [status.value for status in permitidos]


class SolicitacaoEscritaSerializer(serializers.Serializer):
    titulo = serializers.CharField(
        max_length=150,
        min_length=3,
        error_messages={
            'min_length': 'Informe um título com pelo menos 3 caracteres.',
            'blank': 'Informe um título.',
        },
    )
    descricao = serializers.CharField()
    categoria = serializers.PrimaryKeyRelatedField(queryset=Categoria.objects.all())

    def validate_categoria(self, categoria):
        if not categoria.ativa:  # RN09
            raise serializers.ValidationError('Esta categoria está inativa.')
        return categoria


class AlterarStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Solicitacao.Status.choices)


class HistoricoStatusSerializer(serializers.ModelSerializer):
    alterado_por = UsuarioResumoSerializer(read_only=True)
    status_anterior_display = serializers.CharField(
        source='get_status_anterior_display', read_only=True
    )
    status_novo_display = serializers.CharField(
        source='get_status_novo_display', read_only=True
    )

    class Meta:
        model = HistoricoStatus
        fields = (
            'id', 'status_anterior', 'status_anterior_display',
            'status_novo', 'status_novo_display', 'alterado_por', 'alterado_em',
        )


class DashboardSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    abertas = serializers.IntegerField()
    em_atendimento = serializers.IntegerField()
    concluidas = serializers.IntegerField()