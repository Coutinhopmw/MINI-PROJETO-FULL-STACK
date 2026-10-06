from django.contrib import admin

from .models import Categoria, HistoricoStatus, Solicitacao


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativa')
    list_filter = ('ativa',)


class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    readonly_fields = ('alterado_em',)


@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'titulo', 'categoria', 'solicitante', 'status', 'criado_em')
    list_filter = ('status', 'categoria')
    search_fields = ('titulo',)
    inlines = [HistoricoStatusInline]