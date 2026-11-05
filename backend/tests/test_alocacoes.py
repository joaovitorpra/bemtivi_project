from tests.conftest import ANO, MES_NOME


def test_criar_e_listar(client, nova_alocacao, novo_colaborador, nova_demanda):
    r = client.get("/alocacoes", params={"id_colaborador": novo_colaborador["id"]})
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == [nova_alocacao["id"]]

    r = client.get(f"/demandas/{nova_demanda['id']}/alocacoes")
    assert [a["id"] for a in r.json()] == [nova_alocacao["id"]]


def test_alocacao_duplicada(client, nova_alocacao):
    r = client.post("/alocacoes", json={
        "id_colaborador": nova_alocacao["id_colaborador"], "id_demanda": nova_alocacao["id_demanda"],
    })
    assert r.status_code == 409


def test_colaborador_inexistente(client, nova_demanda):
    r = client.post("/alocacoes", json={"id_colaborador": 999999, "id_demanda": nova_demanda["id"]})
    assert r.status_code == 404


def test_planejamento_cria_e_atualiza(client, nova_alocacao):
    aid = nova_alocacao["id"]
    r = client.put(f"/alocacoes/{aid}/planejamentos", json={"mes": MES_NOME, "ano": ANO, "porcentagem": 60})
    assert r.status_code == 200
    r = client.put(f"/alocacoes/{aid}/planejamentos", json={"mes": MES_NOME, "ano": ANO, "porcentagem": 80})
    assert r.status_code == 200

    planejamentos = client.get(f"/alocacoes/{aid}/planejamentos").json()
    assert len(planejamentos) == 1 and planejamentos[0]["porcentagem"] == 80
    assert client.get(f"/alocacoes/{aid}").json()["planejamentos"][0]["porcentagem"] == 80


def test_bloqueia_sobrealocacao(client, nova_alocacao, dados_demanda):
    aid = nova_alocacao["id"]
    client.put(f"/alocacoes/{aid}/planejamentos", json={"mes": MES_NOME, "ano": ANO, "porcentagem": 80})

    outra_demanda = client.post("/demandas", json={**dados_demanda, "nome_demanda": "Outra"}).json()
    outra = client.post("/alocacoes", json={
        "id_colaborador": nova_alocacao["id_colaborador"], "id_demanda": outra_demanda["id"],
    }).json()

    r = client.put(f"/alocacoes/{outra['id']}/planejamentos", json={"mes": MES_NOME, "ano": ANO, "porcentagem": 30})
    assert r.status_code == 409
    assert "20%" in r.json()["detail"]

    r = client.put(f"/alocacoes/{outra['id']}/planejamentos", json={"mes": MES_NOME, "ano": ANO, "porcentagem": 20})
    assert r.status_code == 200


def test_mes_invalido(client, nova_alocacao):
    r = client.put(f"/alocacoes/{nova_alocacao['id']}/planejamentos",
                   json={"mes": "Novembro", "ano": ANO, "porcentagem": 10})
    assert r.status_code == 422


def test_porcentagem_invalida(client, nova_alocacao):
    r = client.put(f"/alocacoes/{nova_alocacao['id']}/planejamentos",
                   json={"mes": MES_NOME, "ano": ANO, "porcentagem": 150})
    assert r.status_code == 422


def test_excluir(client, nova_alocacao):
    aid = nova_alocacao["id"]
    assert client.delete(f"/alocacoes/{aid}").status_code == 204
    assert client.get(f"/alocacoes/{aid}").status_code == 404
