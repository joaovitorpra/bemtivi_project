def test_raiz(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Bem-vindo" in r.json()["message"]


def test_conexao_banco(client):
    r = client.get("/teste-banco")
    assert r.status_code == 200
    assert r.json()["colaboradores"] > 0


def test_tipos_de_dominio(client):
    r = client.get("/dominios/tipos")
    assert r.status_code == 200
    assert "CARGO" in r.json() and "SENIORIDADE" in r.json()


def test_dominios_por_tipo(client):
    r = client.get("/dominios", params={"tipo": "senioridade"})
    assert r.status_code == 200
    assert all(d["tipo_dominio"] == "SENIORIDADE" for d in r.json())


def test_dominio_por_id(client, dominios):
    r = client.get(f"/dominios/{dominios['CARGO']}")
    assert r.status_code == 200
    assert r.json()["tipo_dominio"] == "CARGO"


def test_dominio_inexistente(client):
    assert client.get("/dominios/999999").status_code == 404


def test_busca_skills(client):
    r = client.get("/skills", params={"nome": "java"})
    assert r.status_code == 200
    assert any(s["nome_skill"] == "Java" for s in r.json())
