"""Testes das rotas usadas pelo frontend TalentFlow."""
import pytest

CAMPOS_CANDIDATO = {"id", "name", "role", "source", "avatar", "skills", "engagement",
                    "freeDate", "currentProject", "matchScore", "reason"}


def _buscar(client, prompt):
    r = client.post("/api/ia/buscar", json={"prompt": prompt})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("prompt, skills_esperadas", [
    ("Dev Python sênior disponível agora com foco em backend e banco de dados", {"Python"}),
    ("Especialista Java para microsserviços em nuvem", {"Java", "Microserviços"}),
    ("Front-end React e Tailwind com disponibilidade imediata", {"React", "Tailwind"}),
    ("Product Designer para estruturação de Design System no Figma", {"Figma"}),
])
def test_sugestoes_rapidas_do_frontend(client, prompt, skills_esperadas):
    dados = _buscar(client, prompt)
    assert set(dados["extractedCriteria"]["skills"]) == skills_esperadas
    assert dados["candidates"], "a busca deveria encontrar alguém"
    for cand in dados["candidates"]:
        assert CAMPOS_CANDIDATO <= cand.keys()
        assert cand["source"] in ("INTERNO", "BANCO DE TALENTOS")
        assert 0 <= cand["matchScore"] <= 100


def test_interpreta_senioridade_e_urgencia(client):
    criterios = _buscar(client, "Preciso de um dev Python sênior para agora")["extractedCriteria"]
    assert criterios["seniority"] == "Sênior"
    assert criterios["urgency"] == "Imediata"


def test_interpreta_mes(client):
    criterios = _buscar(client, "Dev React disponível em dezembro")["extractedCriteria"]
    assert criterios["period"].startswith("Dez/")


def test_apelidos_de_skills(client):
    skills = _buscar(client, "Backend com postgres e node")["extractedCriteria"]["skills"]
    assert {"PostgreSQL", "Node.js"} <= set(skills)


def test_nao_confunde_react_native_com_react(client):
    skills = _buscar(client, "Dev React Native")["extractedCriteria"]["skills"]
    assert skills == ["React Native"]


def test_internos_vem_antes_dos_talentos(client):
    origens = [c["source"] for c in _buscar(client, "React e Tailwind")["candidates"]]
    if "BANCO DE TALENTOS" in origens and "INTERNO" in origens:
        assert origens.index("BANCO DE TALENTOS") > max(i for i, o in enumerate(origens) if o == "INTERNO")


def test_sem_skill_reconhecida(client):
    dados = _buscar(client, "alguém comunicativo para liderar o time")
    assert dados["candidates"] == []
    assert dados["message"]


def test_prompt_muito_curto(client):
    assert client.post("/api/ia/buscar", json={"prompt": "a"}).status_code == 422


def test_painel_projetos(client):
    r = client.get("/api/painel/projetos")
    assert r.status_code == 200
    for p in r.json():
        assert {"name", "client", "status", "deadline", "progress"} <= p.keys()
        assert 0 <= p["progress"] <= 100
        assert p["status"] != "Concluída"


def test_painel_equipes(client):
    r = client.get("/api/painel/equipes", params={"limit": 10})
    assert r.status_code == 200 and 0 < len(r.json()) <= 10
    for e in r.json():
        assert {"name", "role", "currentProject", "engagement", "freeDate"} <= e.keys()


def test_painel_equipes_filtro_nome(client):
    r = client.get("/api/painel/equipes", params={"nome": "silva"})
    assert all("silva" in e["name"].lower() for e in r.json())


def test_painel_talentos(client):
    r = client.get("/api/painel/talentos", params={"limit": 10})
    assert r.status_code == 200 and 0 < len(r.json()) <= 10
    for t in r.json():
        assert {"name", "role", "skills", "freeDate"} <= t.keys()
        assert isinstance(t["skills"], list)
