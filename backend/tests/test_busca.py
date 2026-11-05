from tests.conftest import ANO, MES


def test_profissionais_com_skills(client, skill_ids):
    r = client.get("/busca/profissionais", params={
        "ano": ANO, "mes": MES, "skills": list(skill_ids.values()), "disponibilidade_min": 0,
    })
    assert r.status_code == 200
    assert all(p["disponibilidade"] >= 0 for p in r.json())


def test_profissionais_por_cargo(client, dominios):
    r = client.get("/busca/profissionais", params={"ano": ANO, "mes": MES, "cargos": [dominios["CARGO"]]})
    assert r.status_code == 200
    assert all(p["id_cargo"] == dominios["CARGO"] for p in r.json())


def test_ranking_skills(client):
    r = client.get("/busca/ranking-skills", params={"ano": ANO, "mes": MES, "skills": ["Java", "React"], "limit": 5})
    assert r.status_code == 200
    scores = [float(p["score_percentual"]) for p in r.json()]
    assert scores == sorted(scores, reverse=True)


def test_ranking_skills_exige_skills(client):
    assert client.get("/busca/ranking-skills", params={"ano": ANO, "mes": MES}).status_code == 422


def test_ranking_talentos(client):
    r = client.get("/busca/ranking-talentos", params={"skills": ["Java", "React"], "limit": 5})
    assert r.status_code == 200 and len(r.json()) <= 5


def test_disponibilidade_mensal(client):
    r = client.get("/busca/disponibilidade", params={"ano": ANO, "mes": MES, "disponibilidade_min": 100})
    assert r.status_code == 200
    assert all(p["disponibilidade"] >= 100 for p in r.json())


def test_mes_invalido(client):
    assert client.get("/busca/disponibilidade", params={"ano": ANO, "mes": 13}).status_code == 422


def test_disponibilidade_periodo(client):
    r = client.get("/busca/disponibilidade-periodo",
                   params={"ano_inicio": 2026, "mes_inicio": 9, "ano_fim": 2026, "mes_fim": 12})
    assert r.status_code == 200
    assert all(p["meses"] == 4 for p in r.json())


def test_periodo_maior_que_61_meses(client):
    r = client.get("/busca/disponibilidade-periodo",
                   params={"ano_inicio": 2020, "mes_inicio": 1, "ano_fim": 2030, "mes_fim": 12})
    assert r.status_code == 400


def test_sugestoes_para_demanda(client, nova_demanda):
    r = client.get(f"/busca/demandas/{nova_demanda['id']}/sugestoes", params={"ano": ANO, "mes": MES, "limit": 5})
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo["skills_exigidas"]) == {"Java", "React"}
    assert len(corpo["colaboradores"]) <= 5
    assert isinstance(corpo["talentos_externos"], list)


def test_sugestoes_demanda_sem_skills(client, dados_demanda):
    dados_demanda["skills"] = []
    demanda = client.post("/demandas", json=dados_demanda).json()
    r = client.get(f"/busca/demandas/{demanda['id']}/sugestoes", params={"ano": ANO, "mes": MES})
    assert r.status_code == 400
