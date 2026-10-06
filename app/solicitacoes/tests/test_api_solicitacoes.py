import pytest
from rest_framework.test import APIClient

from app.solicitacoes.models import Categoria, HistoricoStatus, Solicitacao

pytestmark = pytest.mark.django_db

Status = Solicitacao.Status
URL = '/api/v1/solicitacoes/'


def url_de(solicitacao, sufixo=''):
    base = f'{URL}{solicitacao.pk}/'
    return f'{base}{sufixo}/' if sufixo else base


def erro_de(resposta):
    return resposta.json()['erro']


def dados_validos(categoria):
    return {'titulo': 'Teclado quebrado', 'descricao': 'Duas teclas travadas.', 'categoria': categoria.pk}


# --- listagem ---

def test_listagem_sem_login_devolve_401(cliente_anonimo):
    assert cliente_anonimo.get(URL).status_code == 401


def test_colaborador_lista_apenas_as_proprias(
    cliente_do_colaborador, fabrica_de_solicitacao, colaborador, outro_colaborador
):
    propria = fabrica_de_solicitacao(colaborador)
    fabrica_de_solicitacao(outro_colaborador)

    resposta = cliente_do_colaborador.get(URL)

    assert resposta.status_code == 200
    assert [item['id'] for item in resposta.json()['results']] == [propria.pk]


def test_atendente_lista_todas(
    cliente_do_atendente, fabrica_de_solicitacao, colaborador, outro_colaborador
):
    fabrica_de_solicitacao(colaborador)
    fabrica_de_solicitacao(outro_colaborador)

    assert cliente_do_atendente.get(URL).json()['count'] == 2


def test_listagem_tem_o_formato_do_contrato(cliente_do_colaborador, solicitacao):
    item = cliente_do_colaborador.get(URL).json()['results'][0]

    assert set(item) == {
        'id', 'codigo', 'titulo', 'categoria', 'solicitante',
        'status', 'status_display', 'criado_em',
    }
    assert item['codigo'] == f'SOL-{solicitacao.pk:06d}'
    assert item['categoria'] == {'id': solicitacao.categoria.pk, 'nome': 'TI'}
    assert set(item['solicitante']) == {'id', 'username', 'nome'}
    assert item['status_display'] == 'Aberto'


def test_listagem_e_paginada_de_dez_em_dez(cliente_do_colaborador, fabrica_de_solicitacao, colaborador):
    for _ in range(12):
        fabrica_de_solicitacao(colaborador)

    pagina_1 = cliente_do_colaborador.get(URL).json()
    pagina_2 = cliente_do_colaborador.get(URL, {'page': 2}).json()

    assert pagina_1['count'] == 12
    assert len(pagina_1['results']) == 10
    assert pagina_1['next'] is not None
    assert len(pagina_2['results']) == 2


# --- criação (RN02, RN09) ---

def test_criar_devolve_201_e_preenche_os_campos_automaticos(
    cliente_do_colaborador, colaborador, categoria_ti
):
    resposta = cliente_do_colaborador.post(URL, dados_validos(categoria_ti), format='json')

    assert resposta.status_code == 201
    assert resposta.json()['status'] == 'ABERTO'
    assert resposta.json()['solicitante']['id'] == colaborador.pk


def test_criar_ignora_status_e_solicitante_enviados_pelo_cliente(
    cliente_do_colaborador, colaborador, atendente, categoria_ti
):
    dados = {**dados_validos(categoria_ti), 'status': 'CONCLUIDO', 'solicitante': atendente.pk}

    resposta = cliente_do_colaborador.post(URL, dados, format='json')

    assert resposta.status_code == 201
    assert resposta.json()['status'] == 'ABERTO'
    assert resposta.json()['solicitante']['id'] == colaborador.pk


def test_criar_com_titulo_curto_devolve_400_com_detalhes_do_campo(
    cliente_do_colaborador, categoria_ti
):
    dados = {**dados_validos(categoria_ti), 'titulo': 'ab'}

    resposta = cliente_do_colaborador.post(URL, dados, format='json')

    assert resposta.status_code == 400
    assert erro_de(resposta)['codigo'] == 'VALIDACAO'
    assert erro_de(resposta)['detalhes']['titulo'] == ['Informe um título com pelo menos 3 caracteres.']


def test_criar_com_categoria_inativa_devolve_400(cliente_do_colaborador, categoria_ti):
    Categoria.objects.filter(pk=categoria_ti.pk).update(ativa=False)

    resposta = cliente_do_colaborador.post(URL, dados_validos(categoria_ti), format='json')

    assert resposta.status_code == 400
    assert 'categoria' in erro_de(resposta)['detalhes']


def test_criar_sem_campos_devolve_400(cliente_do_colaborador):
    resposta = cliente_do_colaborador.post(URL, {}, format='json')

    assert resposta.status_code == 400
    assert {'titulo', 'descricao', 'categoria'} <= set(erro_de(resposta)['detalhes'])


def test_criar_com_sessao_exige_token_csrf(colaborador, categoria_ti):
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.login(username='carla', password='senha-de-teste-1')

    resposta = cliente.post(URL, dados_validos(categoria_ti), format='json')

    assert resposta.status_code == 403
    assert not Solicitacao.objects.exists()


# --- detalhe (RN05) ---

def test_dono_ve_o_detalhe_com_descricao(cliente_do_colaborador, solicitacao):
    resposta = cliente_do_colaborador.get(url_de(solicitacao))

    assert resposta.status_code == 200
    assert resposta.json()['descricao'] == 'Descrição de teste.'
    assert resposta.json()['pode_editar'] is True
    assert resposta.json()['proximos_status'] == []


def test_outro_colaborador_recebe_404_sem_revelar_a_existencia(
    cliente_do_outro_colaborador, solicitacao
):
    assert cliente_do_outro_colaborador.get(url_de(solicitacao)).status_code == 404


def test_atendente_ve_detalhe_e_os_proximos_status(cliente_do_atendente, solicitacao):
    corpo = cliente_do_atendente.get(url_de(solicitacao)).json()

    assert corpo['proximos_status'] == ['EM_ATENDIMENTO']
    assert corpo['pode_editar'] is False


# --- edição (RN03, RN04) ---

def test_dono_edita_solicitacao_aberta(cliente_do_colaborador, solicitacao):
    resposta = cliente_do_colaborador.patch(url_de(solicitacao), {'titulo': 'Novo título'}, format='json')

    assert resposta.status_code == 200
    assert resposta.json()['titulo'] == 'Novo título'


def test_patch_nao_altera_o_status_mesmo_se_enviado(cliente_do_colaborador, solicitacao):
    cliente_do_colaborador.patch(url_de(solicitacao), {'status': 'CONCLUIDO', 'titulo': 'Ok!'}, format='json')

    solicitacao.refresh_from_db()
    assert solicitacao.status == Status.ABERTO


def test_edicao_fora_de_aberto_devolve_409(
    cliente_do_colaborador, fabrica_de_solicitacao, colaborador
):
    solicitacao = fabrica_de_solicitacao(colaborador, status=Status.EM_ATENDIMENTO)

    resposta = cliente_do_colaborador.patch(url_de(solicitacao), {'titulo': 'Tentativa'}, format='json')

    assert resposta.status_code == 409
    assert erro_de(resposta)['codigo'] == 'SOLICITACAO_NAO_EDITAVEL'


def test_atendente_que_nao_e_dono_recebe_403_ao_editar(cliente_do_atendente, solicitacao):
    resposta = cliente_do_atendente.patch(url_de(solicitacao), {'titulo': 'Alheio'}, format='json')

    assert resposta.status_code == 403
    assert erro_de(resposta)['codigo'] == 'SEM_PERMISSAO'


def test_outro_colaborador_recebe_404_ao_editar(cliente_do_outro_colaborador, solicitacao):
    resposta = cliente_do_outro_colaborador.patch(url_de(solicitacao), {'titulo': 'Alheio'}, format='json')

    assert resposta.status_code == 404


def test_put_nao_e_permitido(cliente_do_colaborador, solicitacao, categoria_ti):
    resposta = cliente_do_colaborador.put(url_de(solicitacao), dados_validos(categoria_ti), format='json')

    assert resposta.status_code == 405
    assert erro_de(resposta)['codigo'] == 'METODO_NAO_PERMITIDO'


# --- exclusão (RN03, RN04) ---

def test_dono_exclui_solicitacao_aberta(cliente_do_colaborador, solicitacao):
    assert cliente_do_colaborador.delete(url_de(solicitacao)).status_code == 204
    assert not Solicitacao.objects.filter(pk=solicitacao.pk).exists()


def test_exclusao_fora_de_aberto_devolve_409(
    cliente_do_colaborador, fabrica_de_solicitacao, colaborador
):
    solicitacao = fabrica_de_solicitacao(colaborador, status=Status.CONCLUIDO)

    resposta = cliente_do_colaborador.delete(url_de(solicitacao))

    assert resposta.status_code == 409
    assert Solicitacao.objects.filter(pk=solicitacao.pk).exists()


def test_atendente_que_nao_e_dono_recebe_403_ao_excluir(cliente_do_atendente, solicitacao):
    assert cliente_do_atendente.delete(url_de(solicitacao)).status_code == 403


# --- status (RN06, RN07, RN08) ---

def test_colaborador_nao_altera_status(cliente_do_colaborador, solicitacao):
    resposta = cliente_do_colaborador.post(
        url_de(solicitacao, 'status'), {'status': 'EM_ATENDIMENTO'}, format='json'
    )

    assert resposta.status_code == 403


def test_atendente_altera_status_e_gera_historico(cliente_do_atendente, solicitacao, atendente):
    resposta = cliente_do_atendente.post(
        url_de(solicitacao, 'status'), {'status': 'EM_ATENDIMENTO'}, format='json'
    )

    assert resposta.status_code == 200
    assert resposta.json()['status'] == 'EM_ATENDIMENTO'
    assert resposta.json()['proximos_status'] == ['CONCLUIDO']
    registro = HistoricoStatus.objects.get(solicitacao=solicitacao)
    assert registro.alterado_por == atendente


def test_transicao_invalida_devolve_409_com_mensagem_do_contrato(
    cliente_do_atendente, fabrica_de_solicitacao, colaborador
):
    solicitacao = fabrica_de_solicitacao(colaborador, status=Status.CONCLUIDO)

    resposta = cliente_do_atendente.post(
        url_de(solicitacao, 'status'), {'status': 'ABERTO'}, format='json'
    )

    assert resposta.status_code == 409
    assert erro_de(resposta)['codigo'] == 'TRANSICAO_INVALIDA'
    assert erro_de(resposta)['mensagem'] == 'Não é possível alterar o status de Concluído para Aberto.'


def test_status_inexistente_devolve_400(cliente_do_atendente, solicitacao):
    resposta = cliente_do_atendente.post(
        url_de(solicitacao, 'status'), {'status': 'XYZ'}, format='json'
    )

    assert resposta.status_code == 400
    assert 'status' in erro_de(resposta)['detalhes']


def test_alterar_status_de_solicitacao_inexistente_devolve_404(cliente_do_atendente):
    resposta = cliente_do_atendente.post(f'{URL}99999/status/', {'status': 'EM_ATENDIMENTO'}, format='json')

    assert resposta.status_code == 404


# --- histórico ---

def test_dono_ve_o_historico_em_ordem(
    cliente_do_colaborador, cliente_do_atendente, solicitacao
):
    for novo in ('EM_ATENDIMENTO', 'CONCLUIDO'):
        cliente_do_atendente.post(url_de(solicitacao, 'status'), {'status': novo}, format='json')

    resposta = cliente_do_colaborador.get(url_de(solicitacao, 'historico'))

    assert resposta.status_code == 200
    assert [r['status_novo'] for r in resposta.json()] == ['EM_ATENDIMENTO', 'CONCLUIDO']
    assert resposta.json()[0]['alterado_por']['username'] == 'ana'


def test_outro_colaborador_nao_ve_o_historico(cliente_do_outro_colaborador, solicitacao):
    assert cliente_do_outro_colaborador.get(url_de(solicitacao, 'historico')).status_code == 404


# --- dashboard e categorias ---

def test_dashboard_respeita_o_escopo_do_perfil(
    cliente_do_colaborador, cliente_do_atendente, fabrica_de_solicitacao, colaborador, outro_colaborador
):
    fabrica_de_solicitacao(colaborador, status=Status.ABERTO)
    fabrica_de_solicitacao(outro_colaborador, status=Status.CONCLUIDO)

    assert cliente_do_colaborador.get('/api/v1/dashboard/').json() == {
        'total': 1, 'abertas': 1, 'em_atendimento': 0, 'concluidas': 0,
    }
    assert cliente_do_atendente.get('/api/v1/dashboard/').json()['total'] == 2


def test_categorias_devolve_somente_as_ativas(cliente_do_colaborador):
    Categoria.objects.filter(nome='RH').update(ativa=False)

    resposta = cliente_do_colaborador.get('/api/v1/categorias/')

    nomes = {item['nome'] for item in resposta.json()}
    assert resposta.status_code == 200
    assert 'RH' not in nomes and 'TI' in nomes


def test_dashboard_e_categorias_exigem_login(cliente_anonimo):
    assert cliente_anonimo.get('/api/v1/dashboard/').status_code == 401
    assert cliente_anonimo.get('/api/v1/categorias/').status_code == 401