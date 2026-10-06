import django_filters
from django import forms

from app.solicitacoes.models import Categoria, Solicitacao


class FormularioDeFiltroDeSolicitacao(forms.Form):
    def clean(self):
        dados = super().clean()
        data_inicio = dados.get('data_inicio')
        data_fim = dados.get('data_fim')
        if data_inicio and data_fim and data_inicio > data_fim:  # RN10
            raise forms.ValidationError('A data inicial não pode ser posterior à data final.')
        return dados


class FiltroDeSolicitacao(django_filters.FilterSet):
    data_inicio = django_filters.DateFilter(field_name='criado_em', lookup_expr='date__gte')
    data_fim = django_filters.DateFilter(field_name='criado_em', lookup_expr='date__lte')
    categoria = django_filters.ModelChoiceFilter(queryset=Categoria.objects.all())
    status = django_filters.ChoiceFilter(choices=Solicitacao.Status.choices)
    q = django_filters.CharFilter(field_name='titulo', lookup_expr='icontains')

    class Meta:
        model = Solicitacao
        form = FormularioDeFiltroDeSolicitacao
        fields = []