import itertools

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from app.accounts.models import Usuario
from app.solicitacoes.models import Categoria, Solicitacao


@pytest.fixture(autouse=True)
def limpar_cache():
    # O throttle do login usa o cache; sem isso, as tentativas vazam entre testes.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def categoria_ti():
    return Categoria.objects.get(nome='TI')


@pytest.fixture
def colaborador():
    return Usuario.objects.create_user(username='carla', password='senha-de-teste-1')


@pytest.fixture
def outro_colaborador():
    return Usuario.objects.create_user(username='caio', password='senha-de-teste-3')


@pytest.fixture
def atendente():
    return Usuario.objects.create_user(
        username='ana',
        password='senha-de-teste-2',
        perfil=Usuario.Perfil.ATENDENTE,
    )


@pytest.fixture
def fabrica_de_solicitacao(categoria_ti):
    contador = itertools.count(1)

    def criar(solicitante, status=Solicitacao.Status.ABERTO, **extras):
        return Solicitacao.objects.create(
            titulo=extras.pop('titulo', f'Solicitação {next(contador)}'),
            descricao=extras.pop('descricao', 'Descrição de teste.'),
            categoria=extras.pop('categoria', categoria_ti),
            solicitante=solicitante,
            status=status,
            **extras,
        )

    return criar


@pytest.fixture
def solicitacao(fabrica_de_solicitacao, colaborador):
    return fabrica_de_solicitacao(colaborador)


@pytest.fixture
def cliente_anonimo():
    return APIClient()


def _cliente_autenticado(usuario):
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente


@pytest.fixture
def cliente_do_colaborador(colaborador):
    return _cliente_autenticado(colaborador)


@pytest.fixture
def cliente_do_outro_colaborador(outro_colaborador):
    return _cliente_autenticado(outro_colaborador)


@pytest.fixture
def cliente_do_atendente(atendente):
    return _cliente_autenticado(atendente)