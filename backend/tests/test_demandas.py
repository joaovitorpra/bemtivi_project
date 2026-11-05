def test_listar(client):
    r = client.get("/demandas", params={"limit": 5})
    assert r.status_code == 200 and len(r.json()) <= 5


def test_criar_com_skills(client, nova_demanda, skill_ids):
    assert nova_demanda["nome_demanda"] == "Demanda de Teste"
    assert {s["id"] for s in nova_demanda["skills"]} == set(skill_ids.values())


def test_datas_invertidas(client, dados_demanda):
    dados_demanda["dt_termino_demanda_prevista"] = "2020-01-01"
    assert client.post("/demandas", json=dados_demanda).status_code == 422


def test_skill_inexistente(client, dados_demanda):
    dados_demanda["skills"] = [999999]
    r = client.post("/demandas", json=dados_demanda)
    assert r.status_code == 400
    assert "999999" in r.json()["detail"]


def test_obter(client, nova_demanda):
    r = client.get(f"/demandas/{nova_demanda['id']}")
    assert r.status_code == 200


def test_atualizar(client, nova_demanda):
    r = client.patch(f"/demandas/{nova_demanda['id']}", json={"pertence_pmo": True})
    assert r.status_code == 200 and r.json()["pertence_pmo"] is True


def test_atualizar_datas_invalidas(client, nova_demanda):
    r = client.patch(f"/demandas/{nova_demanda['id']}", json={"dt_termino_demanda_prevista": "2020-01-01"})
    assert r.status_code == 422


def test_substituir_skills(client, nova_demanda, skill_ids):
    r = client.put(f"/demandas/{nova_demanda['id']}/skills", json=[skill_ids["Java"]])
    assert r.status_code == 200
    assert [s["nome_skill"] for s in r.json()] == ["Java"]


def test_excluir(client, nova_demanda):
    did = nova_demanda["id"]
    assert client.delete(f"/demandas/{did}").status_code == 204
    assert client.get(f"/demandas/{did}").status_code == 404


def test_demanda_inexistente(client):
    assert client.get("/demandas/999999").status_code == 404
