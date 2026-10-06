from django.db import migrations

CATEGORIAS_INICIAIS = ['TI', 'RH', 'Compras', 'Financeiro', 'Infraestrutura']


def criar_categorias(apps, schema_editor):
    Categoria = apps.get_model('solicitacoes', 'Categoria')
    for nome in CATEGORIAS_INICIAIS:
        Categoria.objects.get_or_create(nome=nome)


def remover_categorias(apps, schema_editor):
    Categoria = apps.get_model('solicitacoes', 'Categoria')
    Categoria.objects.filter(nome__in=CATEGORIAS_INICIAIS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('solicitacoes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_categorias, remover_categorias),
    ]