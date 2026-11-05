"""
Configuração dos testes.

IMPORTANTE: cada teste roda dentro de uma transação que é DESFEITA (rollback)
no final. Os testes podem criar, editar e excluir à vontade: nada fica gravado
no banco do Supabase.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.main import app

ANO, MES, MES_NOME = 2026, 11, "Nov"


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transacao = connection.begin()
    # os db.commit() da API viram "savepoints" dentro desta transação
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transacao.rollback()  # desfaz tudo que o teste fez
    connection.close()


@pytest.fixture()
def client(db_session):
    def _get_db_teste():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_teste
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ------------------------------------------------------------ dados de apoio
def _primeiro_dominio(client, tipo):
    resp = client.get("/dominios", params={"tipo": tipo})
    assert resp.status_code == 200 and resp.json(), f"Nenhum domínio do tipo {tipo}"
    return resp.json()[0]["id"]


@pytest.fixture()
def dominios(client):
    tipos = ["CARGO", "SENIORIDADE", "STEP", "VINCULO", "MODALIDADE", "TIPO_SERVICO", "ANDAMENTO_DEMANDA"]
    return {t: _primeiro_dominio(client, t) for t in tipos}


@pytest.fixture()
def skill_ids(client):
    """IDs das skills Java e React."""
    ids = {}
    for nome in ("Java", "React"):
        lista = client.get("/skills", params={"nome": nome}).json()
        ids[nome] = next(s["id"] for s in lista if s["nome_skill"] == nome)
    return ids


@pytest.fixture()
def novo_colaborador(client, dominios):
    resp = client.post("/colaboradores", json={
        "nome_abreviado": "Colaborador de Teste",
        "id_cargo": dominios["CARGO"],
        "id_senioridade": dominios["SENIORIDADE"],
        "id_step": dominios["STEP"],
        "id_vinculo": dominios["VINCULO"],
        "id_modalidade": dominios["MODALIDADE"],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def dados_demanda(client, dominios, novo_colaborador, skill_ids):
    contrato_id = client.get("/contratos").json()[0]["id"]
    return {
        "nome_demanda": "Demanda de Teste",
        "id_gerente": novo_colaborador["id"],
        "id_contrato": contrato_id,
        "id_tipo_servico": dominios["TIPO_SERVICO"],
        "id_andamento_demanda": dominios["ANDAMENTO_DEMANDA"],
        "dt_inicio_demanda": "2026-11-01",
        "dt_termino_demanda_prevista": "2027-03-31",
        "skills": list(skill_ids.values()),
    }


@pytest.fixture()
def nova_demanda(client, dados_demanda):
    resp = client.post("/demandas", json=dados_demanda)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def nova_alocacao(client, novo_colaborador, nova_demanda):
    resp = client.post("/alocacoes", json={
        "id_colaborador": novo_colaborador["id"], "id_demanda": nova_demanda["id"],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()
