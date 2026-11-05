"""Testes da página Utilização (indicadores, oportunidades e botão Alocar) e do selo em Equipes."""
from app.api.utilizacao import ANDAMENTOS_ENCERRADOS, HORAS_MES
from tests.conftest import ANO, MES, MES_NOME

URL = "/api/utilizacao"


# ------------------------------------------------------------ apoio
def _indicadores(client, **params):
    r = client.get(f"{URL}/indicadores", params={"ano": ANO, "mes": MES, **params})
    assert r.status_code == 200, r.text
    return r.json()


def _criar_colaborador(client, dominios, nome="Pessoa Utilizacao Teste"):
    r = client.post("/colaboradores", json={
        "nome_abreviado": nome, "id_cargo": dominios["CARGO"], "id_senioridade": dominios["SENIORIDADE"],
        "id_step": dominios["STEP"], "id_vinculo": dominios["VINCULO"], "id_modalidade": dominios["MODALIDADE"],
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _planejar(client, id_colaborador, id_demanda, porcentagem):
    aloc = client.post("/alocacoes", json={"id_colaborador": id_colaborador, "id_demanda": id_demanda})
    assert aloc.status_code == 201, aloc.text
    r = client.put(f"/alocacoes/{aloc.json()['id']}/planejamentos",
                   json={"mes": MES_NOME, "ano": ANO, "porcentagem": porcentagem})
    assert r.status_code == 200, r.text
    return aloc.json()["id"]


def _demanda_em_andamento(client, dados_demanda, nome):
    """Cria uma demanda com andamento não encerrado (só essas recebem sugestões de encaixe)."""
    andamento = next(d["id"] for d in client.get("/dominios", params={"tipo": "ANDAMENTO_DEMANDA"}).json()
                     if d["valor_dominio"] not in ANDAMENTOS_ENCERRADOS)
    r = client.post("/demandas", json={**dados_demanda, "nome_demanda": nome, "id_andamento_demanda": andamento})
    assert r.status_code == 201, r.text
    return r.json()


def _dar_skills(client, id_colaborador, skill_ids):
    for sid in skill_ids:
        r = client.post(f"/colaboradores/{id_colaborador}/skills",
                        json={"id_skill": sid, "nivel_conhecimento": "AVANCADO"})
        assert r.status_code == 201, r.text


# ------------------------------------------------------------ indicadores
def test_indicadores_formato(client):
    dados = _indicadores(client)
    assert dados["hoursPerMonth"] == HORAS_MES == 160
    assert len(dados["trend"]) == 6
    assert dados["current"] == dados["trend"][0]
    assert dados["current"]["period"] == f"{MES_NOME}/{ANO}"
    for m in dados["trend"]:
        assert 0 <= m["averageOccupancy"] <= 100
        assert m["plannedEmployees"] + m["unplanned"] == dados["totalEmployees"]
        assert m["fullyAllocated"] + m["partial"] + m["free"] == m["plannedEmployees"]
        assert m["idleFte"] == round(m["idleHours"] / HORAS_MES, 1)


def test_indicadores_quantidade_de_meses(client):
    trend = _indicadores(client, meses=3)["trend"]
    assert [m["period"] for m in trend] == ["Nov/2026", "Dez/2026", "Jan/2027"]


def test_sem_planejamento_nao_conta_como_ocioso(client, dominios):
    antes = _indicadores(client)["current"]
    _criar_colaborador(client, dominios)
    depois = _indicadores(client)["current"]
    assert depois["unplanned"] == antes["unplanned"] + 1
    assert depois["idleHours"] == antes["idleHours"]
    assert depois["plannedEmployees"] == antes["plannedEmployees"]


def test_parcial_soma_horas_ociosas(client, dominios, nova_demanda):
    antes = _indicadores(client)["current"]
    colab = _criar_colaborador(client, dominios)
    _planejar(client, colab, nova_demanda["id"], 40)
    depois = _indicadores(client)["current"]
    assert depois["partial"] == antes["partial"] + 1
    assert depois["idleHours"] == antes["idleHours"] + 96  # 60% de 160 h


# ------------------------------------------------------------ oportunidades
def test_oportunidade_com_sugestao_de_encaixe(client, dominios, nova_demanda, dados_demanda, skill_ids):
    colab = _criar_colaborador(client, dominios)
    _dar_skills(client, colab, skill_ids.values())                 # Java e React
    _planejar(client, colab, nova_demanda["id"], 40)
    outra = _demanda_em_andamento(client, dados_demanda, "Demanda Encaixe")

    r = client.get(f"{URL}/oportunidades", params={"ano": ANO, "mes": MES, "limit": 200, "id_demanda": outra["id"]})
    assert r.status_code == 200, r.text
    pessoa = next(p for p in r.json()["opportunities"] if p["id"] == colab)
    assert pessoa["occupancy"] == 40
    assert pessoa["freePercent"] == 60 and pessoa["freeHours"] == 96
    sugestao = pessoa["suggestions"][0]
    assert sugestao["demandId"] == outra["id"]
    assert sugestao["matchScore"] == 100
    assert set(sugestao["matchedSkills"]) == {"Java", "React"}
    assert sugestao["suggestedPercent"] == 60


def test_nao_sugere_demanda_em_que_ja_esta(client, dominios, dados_demanda, skill_ids):
    demanda = _demanda_em_andamento(client, dados_demanda, "Demanda Atual")
    colab = _criar_colaborador(client, dominios)
    _dar_skills(client, colab, skill_ids.values())
    _planejar(client, colab, demanda["id"], 40)
    r = client.get(f"{URL}/oportunidades", params={"ano": ANO, "mes": MES, "limit": 200, "id_demanda": demanda["id"]})
    assert all(p["id"] != colab for p in r.json()["opportunities"])


def test_oportunidades_nao_inclui_ocupados_nem_sem_planejamento(client, dominios, nova_demanda):
    ocupado = _criar_colaborador(client, dominios, "Pessoa Ocupada Teste")
    _planejar(client, ocupado, nova_demanda["id"], 100)
    sem_plano = _criar_colaborador(client, dominios, "Pessoa Sem Plano Teste")
    ids = {p["id"] for p in client.get(f"{URL}/oportunidades",
                                       params={"ano": ANO, "mes": MES, "limit": 200}).json()["opportunities"]}
    assert ocupado not in ids and sem_plano not in ids


# ------------------------------------------------------------ alocar
def test_alocar_cria_alocacao_e_planejamento(client, dominios, nova_demanda, dados_demanda):
    colab = _criar_colaborador(client, dominios)
    _planejar(client, colab, nova_demanda["id"], 40)
    outra = client.post("/demandas", json={**dados_demanda, "nome_demanda": "Demanda Alocar"}).json()

    r = client.post(f"{URL}/alocar", json={"id_colaborador": colab, "id_demanda": outra["id"],
                                           "ano": ANO, "mes": MES, "porcentagem": 60})
    assert r.status_code == 201, r.text
    resp = r.json()
    assert resp["createdAllocation"] is True
    assert resp["occupancyBefore"] == 40 and resp["occupancyAfter"] == 100

    planos = client.get(f"/alocacoes/{resp['allocationId']}/planejamentos").json()
    assert [(p["mes"], p["ano"], p["porcentagem"]) for p in planos] == [(MES_NOME, ANO, 60)]


def test_nao_sugere_demanda_encerrada(client, dominios, nova_demanda, dados_demanda, skill_ids):
    encerrada = next((d["id"] for d in client.get("/dominios", params={"tipo": "ANDAMENTO_DEMANDA"}).json()
                      if d["valor_dominio"] in ANDAMENTOS_ENCERRADOS), None)
    if encerrada is None:
        return  # o banco não tem andamento encerrado cadastrado
    demanda = client.post("/demandas", json={**dados_demanda, "nome_demanda": "Demanda Encerrada",
                                             "id_andamento_demanda": encerrada}).json()
    colab = _criar_colaborador(client, dominios)
    _dar_skills(client, colab, skill_ids.values())
    _planejar(client, colab, nova_demanda["id"], 40)
    r = client.get(f"{URL}/oportunidades", params={"ano": ANO, "mes": MES, "limit": 200, "id_demanda": demanda["id"]})
    assert all(p["id"] != colab for p in r.json()["opportunities"])


def test_alocar_bloqueia_sobrealocacao_sem_gravar_nada(client, dominios, nova_demanda, dados_demanda):
    colab = _criar_colaborador(client, dominios)
    _planejar(client, colab, nova_demanda["id"], 40)
    outra = client.post("/demandas", json={**dados_demanda, "nome_demanda": "Demanda Cheia"}).json()

    r = client.post(f"{URL}/alocar", json={"id_colaborador": colab, "id_demanda": outra["id"],
                                           "ano": ANO, "mes": MES, "porcentagem": 70})
    assert r.status_code == 409
    assert "60%" in r.json()["detail"]
    alocacoes = client.get("/alocacoes", params={"id_colaborador": colab}).json()
    assert [a["id_demanda"] for a in alocacoes] == [nova_demanda["id"]]  # nenhuma alocação nova


def test_alocar_em_demanda_que_ja_esta_atualiza_o_mes(client, dominios, nova_demanda):
    colab = _criar_colaborador(client, dominios)
    aid = _planejar(client, colab, nova_demanda["id"], 40)
    r = client.post(f"{URL}/alocar", json={"id_colaborador": colab, "id_demanda": nova_demanda["id"],
                                           "ano": ANO, "mes": MES, "porcentagem": 80})
    assert r.status_code == 201, r.text
    assert r.json()["createdAllocation"] is False and r.json()["allocationId"] == aid
    assert client.get(f"/alocacoes/{aid}/planejamentos").json()[0]["porcentagem"] == 80


def test_alocar_colaborador_inexistente(client, nova_demanda):
    r = client.post(f"{URL}/alocar", json={"id_colaborador": 999999, "id_demanda": nova_demanda["id"],
                                           "ano": ANO, "mes": MES, "porcentagem": 10})
    assert r.status_code == 404


def test_alocar_porcentagem_invalida(client, novo_colaborador, nova_demanda):
    for pct in (0, 150):
        r = client.post(f"{URL}/alocar", json={"id_colaborador": novo_colaborador["id"],
                                               "id_demanda": nova_demanda["id"],
                                               "ano": ANO, "mes": MES, "porcentagem": pct})
        assert r.status_code == 422


# ------------------------------------------------------------ selo em Equipes
def test_equipes_traz_situacao_do_planejamento(client):
    r = client.get("/api/painel/equipes", params={"limit": 20})
    assert r.status_code == 200
    for e in r.json():
        assert e["planningStatus"] in {"livre", "parcial", "ocupado", "sem_planejamento"}


def test_equipes_marca_sem_planejamento(client, dominios, nova_demanda):
    sem_plano = _criar_colaborador(client, dominios, "Selo Sem Plano Teste")
    parcial = _criar_colaborador(client, dominios, "Selo Parcial Teste")
    _planejar(client, parcial, nova_demanda["id"], 50)

    cards = {e["id"]: e for e in client.get("/api/painel/equipes", params={"nome": "Selo"}).json()}
    if cards[parcial]["engagement"] == 50:  # o painel usa o mês atual; só confere se for Nov/2026
        assert cards[parcial]["planningStatus"] == "parcial"
        assert cards[parcial]["unplannedFrom"] == "Dez/2026"
    assert cards[sem_plano]["planningStatus"] == "sem_planejamento"
    assert cards[sem_plano]["currentProject"] == "Sem planejamento no mês"
