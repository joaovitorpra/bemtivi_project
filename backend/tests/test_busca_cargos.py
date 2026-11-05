"""Testes da busca de IA por cargo e da inclusão de pessoas parcialmente disponíveis."""
import pytest

from app.api.talentflow import LIMITE_INTERNOS, LIMITE_PARCIAIS, _selecionar_internos
from tests.test_utilizacao import _criar_colaborador, _dar_skills, _planejar

CARGO = "Engenheiro de Soluções"


def _buscar(client, prompt):
    r = client.post("/api/ia/buscar", json={"prompt": prompt})
    assert r.status_code == 200, r.text
    return r.json()


def _id_cargo(client, nome):
    cargos = client.get("/dominios", params={"tipo": "CARGO"}).json()
    cid = next((d["id"] for d in cargos if d["valor_dominio"] == nome), None)
    if cid is None:
        pytest.skip(f"cargo {nome!r} não cadastrado neste banco")
    return cid


@pytest.fixture()
def engenheiro(client, dominios, nova_demanda, skill_ids):
    """Colaborador com o cargo, Java e React, 40% alocado no mês (60% livre)."""
    colab = _criar_colaborador(client, {**dominios, "CARGO": _id_cargo(client, CARGO)}, "Engenheira Teste Busca")
    _dar_skills(client, colab, skill_ids.values())
    _planejar(client, colab, nova_demanda["id"], 40)
    return colab


# ------------------------------------------------------------ reconhecimento do cargo no texto
def test_reconhece_cargo(client):
    _id_cargo(client, CARGO)
    assert _buscar(client, "Preciso de um Engenheiro de Soluções")["extractedCriteria"]["roles"] == [CARGO]


def test_reconhece_cargo_sem_acento_e_minusculo(client):
    _id_cargo(client, CARGO)
    assert _buscar(client, "engenheiro de solucoes")["extractedCriteria"]["roles"] == [CARGO]


def test_cargo_mais_longo_tem_prioridade(client):
    _id_cargo(client, "Analista de Sistemas Desenvolvedor")
    roles = _buscar(client, "Analista de Sistemas Desenvolvedor com Java")["extractedCriteria"]["roles"]
    assert roles == ["Analista de Sistemas Desenvolvedor"]


def test_estagiario_continua_sendo_senioridade(client):
    criterios = _buscar(client, "Estagiário com Java")["extractedCriteria"]
    assert criterios["roles"] == []
    assert criterios["seniority"] == "Estagiário"


def test_palavra_comum_nao_vira_cargo(client):
    assert _buscar(client, "Trabalho contínuo com Java")["extractedCriteria"]["roles"] == []


# ------------------------------------------------------------ resultados
def test_busca_so_por_cargo(client, engenheiro):
    dados = _buscar(client, CARGO)
    assert dados["extractedCriteria"]["skills"] == []
    internos = [c for c in dados["candidates"] if c["source"] == "INTERNO"]
    assert f"int-{engenheiro}" in [c["id"] for c in internos]
    assert all(c["role"] == CARGO for c in dados["candidates"])
    eu = next(c for c in internos if c["id"] == f"int-{engenheiro}")
    assert eu["availability"] == 60 and "parcialmente" in eu["reason"].lower()


def test_cargo_com_skill_filtra_pelo_cargo(client, engenheiro):
    dados = _buscar(client, f"{CARGO} com Java")
    assert dados["extractedCriteria"]["roles"] == [CARGO]
    assert dados["extractedCriteria"]["skills"] == ["Java"]
    internos = [c for c in dados["candidates"] if c["source"] == "INTERNO"]
    assert f"int-{engenheiro}" in [c["id"] for c in internos]
    assert all(c["role"] == CARGO for c in internos)


def test_candidatos_trazem_disponibilidade(client):
    for c in _buscar(client, "Dev Java")["candidates"]:
        assert 0 <= c["availability"] <= 100
        if c["source"] == "INTERNO":
            assert c["availability"] >= 1


def test_internos_no_maximo_cinco_mais_parciais(client):
    internos = [c for c in _buscar(client, "Dev Java")["candidates"] if c["source"] == "INTERNO"]
    assert len(internos) <= LIMITE_INTERNOS + LIMITE_PARCIAIS
    assert all(c["availability"] < 100 for c in internos[LIMITE_INTERNOS:])


def test_sem_skill_nem_cargo(client):
    dados = _buscar(client, "alguém comunicativo para liderar o time")
    assert dados["candidates"] == [] and "cargo" in dados["message"]


# ------------------------------------------------------------ regra de seleção (sem banco)
def _linhas(*disps):
    return [{"id": i, "disponibilidade": d} for i, d in enumerate(disps)]


def test_selecao_acrescenta_parciais_depois_dos_cinco():
    linhas = _linhas(100, 100, 100, 100, 100, 100, 60, 100, 30, 80, 10)
    ids = [l["id"] for l in _selecionar_internos(linhas)]
    assert ids == [0, 1, 2, 3, 4, 6, 8, 9]  # 5 primeiros + 3 parciais, na ordem do ranking


def test_selecao_parcial_ja_no_top_nao_duplica():
    linhas = _linhas(100, 50, 100, 100, 100, 100, 40)
    assert [l["id"] for l in _selecionar_internos(linhas)] == [0, 1, 2, 3, 4, 6]


def test_selecao_lista_curta():
    assert [l["id"] for l in _selecionar_internos(_linhas(100, 20))] == [0, 1]
    assert _selecionar_internos([]) == []
