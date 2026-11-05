def test_listar(client):
    r = client.get("/colaboradores", params={"limit": 5})
    assert r.status_code == 200
    assert 0 < len(r.json()) <= 5


def test_filtrar_por_nome(client):
    r = client.get("/colaboradores", params={"nome": "silva"})
    assert r.status_code == 200
    assert all("silva" in c["nome_abreviado"].lower() for c in r.json())


def test_criar_e_obter(client, novo_colaborador):
    r = client.get(f"/colaboradores/{novo_colaborador['id']}")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["nome_abreviado"] == "Colaborador de Teste"
    assert corpo["cargo"] is not None
    assert corpo["skills"] == []


def test_criar_com_fk_invalida(client, dominios):
    r = client.post("/colaboradores", json={
        "nome_abreviado": "X", "id_cargo": 999999, "id_senioridade": dominios["SENIORIDADE"],
        "id_step": dominios["STEP"], "id_vinculo": dominios["VINCULO"], "id_modalidade": dominios["MODALIDADE"],
    })
    assert r.status_code == 409


def test_criar_sem_nome(client, dominios):
    r = client.post("/colaboradores", json={"nome_abreviado": "", "id_cargo": dominios["CARGO"]})
    assert r.status_code == 422


def test_atualizar(client, novo_colaborador):
    r = client.patch(f"/colaboradores/{novo_colaborador['id']}", json={"nome_abreviado": "Nome Novo"})
    assert r.status_code == 200
    assert r.json()["nome_abreviado"] == "Nome Novo"


def test_excluir(client, novo_colaborador):
    cid = novo_colaborador["id"]
    assert client.delete(f"/colaboradores/{cid}").status_code == 204
    assert client.get(f"/colaboradores/{cid}").status_code == 404


def test_colaborador_inexistente(client):
    assert client.get("/colaboradores/999999").status_code == 404


def test_skills_do_colaborador(client, novo_colaborador, skill_ids):
    cid, java = novo_colaborador["id"], skill_ids["Java"]

    r = client.post(f"/colaboradores/{cid}/skills", json={"id_skill": java, "nivel_conhecimento": "AVANCADO"})
    assert r.status_code == 201
    assert r.json()["nivel_conhecimento"] == "AVANCADO"

    # mesma skill de novo: atualiza o nível em vez de duplicar
    r = client.post(f"/colaboradores/{cid}/skills", json={"id_skill": java, "nivel_conhecimento": "BASICO"})
    assert r.status_code == 201
    skills = client.get(f"/colaboradores/{cid}/skills").json()
    assert len(skills) == 1 and skills[0]["nivel_conhecimento"] == "BASICO"

    assert client.delete(f"/colaboradores/{cid}/skills/{java}").status_code == 204
    assert client.get(f"/colaboradores/{cid}/skills").json() == []


def test_skill_nivel_invalido(client, novo_colaborador, skill_ids):
    r = client.post(f"/colaboradores/{novo_colaborador['id']}/skills",
                    json={"id_skill": skill_ids["Java"], "nivel_conhecimento": "EXPERT"})
    assert r.status_code == 422


def test_skill_inexistente(client, novo_colaborador):
    r = client.post(f"/colaboradores/{novo_colaborador['id']}/skills",
                    json={"id_skill": 999999, "nivel_conhecimento": "BASICO"})
    assert r.status_code == 404
