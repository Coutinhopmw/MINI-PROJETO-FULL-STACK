import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL_LOGIN = '/api/v1/auth/login/'
URL_LOGOUT = '/api/v1/auth/logout/'
URL_ME = '/api/v1/auth/me/'
URL_SOLICITACOES = '/api/v1/solicitacoes/'
CREDENCIAIS_VALIDAS = {'username': 'carla', 'password': 'senha-de-teste-1'}
CREDENCIAIS_ERRADAS = {'username': 'carla', 'password': 'errada'}


def erro_de(resposta):
    return resposta.json()['erro']


def test_login_valido_abre_sessao_e_devolve_o_usuario(cliente_anonimo, colaborador):
    resposta = cliente_anonimo.post(URL_LOGIN, CREDENCIAIS_VALIDAS, format='json')

    assert resposta.status_code == 200
    assert resposta.json()['username'] == 'carla'
    assert resposta.json()['perfil'] == 'COLABORADOR'
    assert 'password' not in resposta.json()
    assert cliente_anonimo.get(URL_ME).status_code == 200  # a sessão ficou no cookie


def test_login_com_senha_errada_devolve_401(cliente_anonimo, colaborador):
    resposta = cliente_anonimo.post(URL_LOGIN, CREDENCIAIS_ERRADAS, format='json')

    assert resposta.status_code == 401
    assert erro_de(resposta)['codigo'] == 'NAO_AUTENTICADO'
    assert cliente_anonimo.get(URL_ME).status_code == 401


def test_login_de_usuario_inativo_devolve_401(cliente_anonimo, colaborador):
    colaborador.is_active = False
    colaborador.save()

    resposta = cliente_anonimo.post(URL_LOGIN, CREDENCIAIS_VALIDAS, format='json')

    assert resposta.status_code == 401


def test_login_sem_campos_devolve_400_com_detalhes(cliente_anonimo):
    resposta = cliente_anonimo.post(URL_LOGIN, {}, format='json')

    assert resposta.status_code == 400
    assert erro_de(resposta)['codigo'] == 'VALIDACAO'
    assert {'username', 'password'} <= set(erro_de(resposta)['detalhes'])


def test_login_limita_as_tentativas_por_minuto(cliente_anonimo, colaborador):
    for _ in range(5):
        cliente_anonimo.post(URL_LOGIN, CREDENCIAIS_ERRADAS, format='json')

    resposta = cliente_anonimo.post(URL_LOGIN, CREDENCIAIS_ERRADAS, format='json')

    assert resposta.status_code == 429
    assert erro_de(resposta)['codigo'] == 'LIMITE_EXCEDIDO'


def test_login_exige_token_csrf(colaborador):
    cliente = APIClient(enforce_csrf_checks=True)

    resposta = cliente.post(URL_LOGIN, CREDENCIAIS_VALIDAS, format='json')

    assert resposta.status_code == 403
    assert erro_de(resposta)['codigo'] == 'SEM_PERMISSAO'


def test_me_sem_login_devolve_401(cliente_anonimo):
    resposta = cliente_anonimo.get(URL_ME)

    assert resposta.status_code == 401
    assert erro_de(resposta)['codigo'] == 'NAO_AUTENTICADO'


def test_logout_encerra_a_sessao(cliente_anonimo, colaborador):
    cliente_anonimo.post(URL_LOGIN, CREDENCIAIS_VALIDAS, format='json')

    resposta = cliente_anonimo.post(URL_LOGOUT)

    assert resposta.status_code == 204
    assert cliente_anonimo.get(URL_ME).status_code == 401


def test_logout_sem_login_devolve_401(cliente_anonimo):
    assert cliente_anonimo.post(URL_LOGOUT).status_code == 401