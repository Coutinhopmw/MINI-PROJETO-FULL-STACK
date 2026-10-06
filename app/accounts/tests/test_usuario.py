import pytest 
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from app.accounts.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario_colaborador():
    return Usuario.objects.create_user(username='carla', password='senha-de-teste-1')


@pytest.fixture
def usuario_atendente():
    return Usuario.objects.create_user(
        username='ana',
        password='senha-de-teste-2',
        perfil=Usuario.Perfil.ATENDENTE,
    )


def test_usuario_novo_nasce_como_colaborador(usuario_colaborador):
    assert usuario_colaborador.perfil == Usuario.Perfil.COLABORADOR


def test_eh_atendente_somente_para_perfil_atendente(usuario_colaborador, usuario_atendente):
    assert usuario_atendente.eh_atendente is True
    assert usuario_colaborador.eh_atendente is False


def test_banco_rejeita_perfil_invalido():
    with pytest.raises(IntegrityError):
        Usuario.objects.create_user(username='intruso', password='x', perfil='CHEFE')


def test_modelo_de_usuario_configurado_e_o_customizado():
    assert get_user_model() is Usuario