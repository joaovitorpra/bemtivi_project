def test_listar_contratos(client):
    r = client.get("/contratos")
    assert r.status_code == 200 and len(r.json()) > 0


def test_contrato_e_relacionados(client):
    contrato_id = client.get("/contratos").json()[0]["id"]
    assert client.get(f"/contratos/{contrato_id}").status_code == 200
    assert client.get(f"/contratos/{contrato_id}/demandas").status_code == 200
    assert client.get(f"/contratos/{contrato_id}/colaboradores").status_code == 200


def test_contrato_inexistente(client):
    assert client.get("/contratos/999999").status_code == 404


def test_listar_talentos(client):
    r = client.get("/talentos", params={"disponibilidade_min": 50, "limit": 10})
    assert r.status_code == 200
    assert all(t["disponibilidade_informada_percentual"] >= 50 for t in r.json())


def test_talento_com_skills(client):
    talento_id = client.get("/talentos", params={"limit": 1}).json()[0]["id"]
    r = client.get(f"/talentos/{talento_id}")
    assert r.status_code == 200
    assert isinstance(r.json()["skills"], list)


def test_talento_inexistente(client):
    assert client.get("/talentos/999999").status_code == 404
