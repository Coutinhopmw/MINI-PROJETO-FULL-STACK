import itertools

import pytest

from app.accounts.models import Usuario
from app.solicitacoes.models import Categoria, Solicitacao


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