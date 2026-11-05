"""
Rotas usadas pelo frontend TalentFlow (React).

Retornam os dados exatamente no formato que as telas esperam:
  POST /api/ia/buscar          -> Assistente de IA (busca em linguagem natural)
  GET  /api/painel/projetos    -> página Projetos
  GET  /api/painel/equipes     -> página Equipes
  GET  /api/painel/talentos    -> página Talentos

A "IA" interpreta o texto por regras: reconhece as skills cadastradas no banco,
a senioridade e o mês/urgência, e usa as funções de ranking do banco para
montar a cascata Banco Interno -> Banco de Talentos.
"""
import datetime
import re
import unicodedata
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api", tags=["Frontend (TalentFlow)"])

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
MESES_EXTENSO = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
                 "agosto", "setembro", "outubro", "novembro", "dezembro"]
SENIORIDADES = {"estagiario": "Estagiário", "trainee": "Trainee", "junior": "Júnior", "pleno": "Pleno",
                "senior": "Sênior", "master": "Master", "especialista": "Especialista"}
# apelidos comuns -> nome da skill no banco
APELIDOS = {
    "postgres": "PostgreSQL", "node": "Node.js", "nodejs": "Node.js", "js": "JavaScript",
    "ts": "TypeScript", "spring": "Spring Boot (Java)", "springboot": "Spring Boot (Java)",
    "microsservicos": "Microserviços", "microsservico": "Microserviços", "k8s": "Kubernetes",
    "golang": "Go", "dotnet": ".NET", "power bi": "PowerBI", "vue": "Vue.js", "ux": "UX/UI",
}
# apelidos comuns -> nome do cargo no banco
APELIDOS_CARGO = {
    "full stack": "Desenvolvedor Full Stack", "fullstack": "Desenvolvedor Full Stack",
    "dba": "Administrador de Bancos de Dados",
}
# cargos que também são senioridade ou palavras comuns no texto: não viram filtro de cargo
CARGOS_IGNORADOS = {"estagiario", "trainee", "continuo"}
LIMITE_INTERNOS = 5
LIMITE_PARCIAIS = 3  # além dos 5 melhores, até 3 pessoas parcialmente disponíveis
LIMITE_TALENTOS = 3
MIN_MATCH_COMPLETO_INTERNO = 3  # abaixo disso, o Banco de Talentos é acionado


# ------------------------------------------------------------------ utilitários
def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def _mes_label(ano: int, mes: int) -> str:
    return f"{MESES[mes - 1]}/{ano}"


def _data_label(data: datetime.date) -> str:
    return f"{data.day:02d} {MESES[data.month - 1]} {data.year}"


def _hoje() -> datetime.date:
    return datetime.date.today()


def _disponibilidade_meses(db: Session, ids: list[int], ano: int, mes: int, n_meses: int) -> dict[int, list]:
    """{id_colaborador: [(ano, mes, disponibilidade), ...]} para os próximos n_meses."""
    if not ids:
        return {}
    inicio = ano * 12 + mes
    rows = db.execute(text("""
        WITH meses AS (
            SELECT ((n - 1) / 12)::int AS ano, ((n - 1) % 12 + 1)::int AS mes
            FROM generate_series(:inicio, :inicio + :n - 1) n
        )
        SELECT m.ano, m.mes, d.id_colaborador, d.disponibilidade
        FROM meses m
        CROSS JOIN LATERAL "InHire".disponibilidade_mensal(m.ano, m.mes) d
        WHERE d.id_colaborador = ANY(CAST(:ids AS bigint[]))
        ORDER BY d.id_colaborador, m.ano, m.mes
    """), {"inicio": inicio, "n": n_meses, "ids": ids}).all()
    resultado: dict[int, list] = {}
    for r in rows:
        resultado.setdefault(r.id_colaborador, []).append((r.ano, r.mes, r.disponibilidade))
    return resultado


def _projetos_atuais(db: Session, ids: list[int], ano: int, mes: int) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.execute(text("""
        SELECT a.id_colaborador, string_agg(DISTINCT d.nome_demanda, ', ') AS projetos
        FROM "InHire".planejamentos p
        JOIN "InHire".alocacoes a ON a.id = p.id_alocacao
        JOIN "InHire".demandas d ON d.id = a.id_demanda
        WHERE p.ano = :ano AND p.mes = :mes AND p.porcentagem > 0
          AND p.status AND NOT p.deletado AND a.status AND NOT a.deletado
          AND a.id_colaborador = ANY(CAST(:ids AS bigint[]))
        GROUP BY a.id_colaborador
    """), {"ano": ano, "mes": MESES[mes - 1], "ids": ids}).all()
    return {r.id_colaborador: r.projetos for r in rows}


def _proximos_meses(ano: int, mes: int, n_meses: int) -> list[tuple[int, int]]:
    """[(ano, mes), ...] a partir do mês informado, inclusive."""
    inicio = ano * 12 + (mes - 1)
    return [((inicio + i) // 12, (inicio + i) % 12 + 1) for i in range(n_meses)]


def _meses_planejados(db: Session, ids: list[int], ano: int, mes: int, n_meses: int) -> dict[int, set]:
    """
    {id_colaborador: {(ano, mes), ...}} com os meses em que existe ALGUM planejamento lançado
    (mesmo que 0%). Serve para separar "livre" de "o gestor não lançou o planejamento".
    """
    if not ids:
        return {}
    meses = _proximos_meses(ano, mes, n_meses)
    rows = db.execute(text("""
        SELECT DISTINCT a.id_colaborador, p.ano, p.mes
        FROM "InHire".planejamentos p
        JOIN "InHire".alocacoes a ON a.id = p.id_alocacao
        WHERE p.status AND NOT p.deletado AND a.status AND NOT a.deletado
          AND a.id_colaborador = ANY(CAST(:ids AS bigint[]))
          AND p.ano BETWEEN :ano_ini AND :ano_fim
    """), {"ids": ids, "ano_ini": meses[0][0], "ano_fim": meses[-1][0]}).all()
    resultado: dict[int, set] = {}
    for r in rows:
        resultado.setdefault(r.id_colaborador, set()).add((r.ano, MESES.index(r.mes) + 1))
    return resultado


def _situacao_planejamento(planejados: set, ano: int, mes: int, ocupacao: int,
                           n_meses: int = 6) -> tuple[str, Optional[str]]:
    """
    Retorna (situação no mês, primeiro mês sem planejamento nos próximos n_meses).
    Situação: "sem_planejamento", "livre", "parcial" ou "ocupado".
    """
    if (ano, mes) not in planejados:
        situacao = "sem_planejamento"
    elif ocupacao >= 100:
        situacao = "ocupado"
    elif ocupacao > 0:
        situacao = "parcial"
    else:
        situacao = "livre"
    lacuna = next((m for m in _proximos_meses(ano, mes, n_meses) if m not in planejados), None)
    return situacao, (_mes_label(*lacuna) if lacuna else None)


def _texto_liberacao(meses: list) -> str:
    """Descreve quando o colaborador fica livre a partir da lista de disponibilidade mensal."""
    if not meses:
        return "Sem previsão"
    _, _, disp_atual = meses[0]
    if disp_atual >= 100:
        return "Disponível agora"
    if disp_atual > 0:
        return f"{disp_atual}% livre agora"
    for ano, mes, disp in meses[1:]:
        if disp > 0:
            return f"A partir de {_mes_label(ano, mes)}"
    return "Sem previsão"


# ------------------------------------------------------------------ interpretação do texto
def _extrair_skills(db: Session, prompt_norm: str) -> list[str]:
    nomes = db.scalars(text(
        'SELECT DISTINCT nome_skill FROM "InHire".skills WHERE status AND NOT deletado'
    )).all()
    candidatos: dict[str, str] = {}
    for nome in nomes:
        base = _normalizar(nome)
        if len(base) < 2 or base == "go":  # "C" e "Go" geram falsos positivos no texto
            continue
        candidatos.setdefault(base, nome)
        if " (" in base:  # "spring boot (java)" -> "spring boot"
            candidatos.setdefault(base.split(" (")[0], nome)
    nomes_existentes = set(nomes)
    for apelido, nome in APELIDOS.items():
        if nome in nomes_existentes:
            candidatos.setdefault(apelido, nome)

    texto = prompt_norm
    encontrados: list[str] = []
    for termo in sorted(candidatos, key=len, reverse=True):  # termos longos primeiro
        padrao = r"(?<![a-z0-9#+.])" + re.escape(termo) + r"(?![a-z0-9#+])"
        if re.search(padrao, texto):
            nome = candidatos[termo]
            if nome not in encontrados:
                encontrados.append(nome)
            texto = re.sub(padrao, " ", texto)  # evita casar "react" dentro de "react native"
    return encontrados


def _extrair_cargos(db: Session, prompt_norm: str) -> list[tuple[int, str]]:
    """[(id_cargo, nome), ...] dos cargos cadastrados citados no texto (sem acento, maiúsc./minúsc.)."""
    cargos = db.execute(text(
        "SELECT id, valor_dominio FROM \"InHire\".dominios "
        "WHERE tipo_dominio = 'CARGO' AND status AND NOT deletado"
    )).all()
    candidatos: dict[str, tuple[int, str]] = {}
    for cid, nome in cargos:
        base = _normalizar(nome).strip()
        if base in CARGOS_IGNORADOS:
            continue
        candidatos.setdefault(base, (cid, nome))
    por_nome = {nome: (cid, nome) for cid, nome in cargos}
    for apelido, nome in APELIDOS_CARGO.items():
        if nome in por_nome:
            candidatos.setdefault(apelido, por_nome[nome])

    texto = prompt_norm
    encontrados: list[tuple[int, str]] = []
    for termo in sorted(candidatos, key=len, reverse=True):  # "analista de sistemas desenvolvedor" antes de "desenvolvedor"
        padrao = r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])"
        if re.search(padrao, texto):
            if candidatos[termo] not in encontrados:
                encontrados.append(candidatos[termo])
            texto = re.sub(padrao, " ", texto)
    return encontrados


def _selecionar_internos(linhas: list, limite: int = LIMITE_INTERNOS, limite_parciais: int = LIMITE_PARCIAIS) -> list:
    """
    As `limite` primeiras linhas do ranking (melhor compatibilidade e mais disponíveis primeiro)
    e mais até `limite_parciais` pessoas parcialmente disponíveis (1% a 99%) que ficaram de fora.
    Mantém a ordem original do ranking.
    """
    escolhidas = list(range(min(limite, len(linhas))))
    parciais = [i for i in range(len(escolhidas), len(linhas)) if linhas[i]["disponibilidade"] < 100]
    escolhidas += parciais[:limite_parciais]
    return [linhas[i] for i in sorted(escolhidas)]


def _ranking_internos(db: Session, ano: int, mes: int, skills: list[str], id_senioridade: Optional[int],
                      ids_cargo: list[int]) -> list:
    """Colaboradores com disponibilidade no mês, já na ordem do ranking (sem limite)."""
    if skills:
        return db.execute(text("""
            SELECT r.* FROM "InHire".ranking_skills(:ano, :mes, CAST(:skills AS text[]), 1, false, :sen) r
            JOIN "InHire".colaboradores c ON c.id = r.id_colaborador
            WHERE cardinality(CAST(:cargos AS bigint[])) = 0 OR c.id_cargo = ANY(CAST(:cargos AS bigint[]))
            ORDER BY r.score_percentual DESC, r.disponibilidade DESC, r.id_colaborador
        """), {"ano": ano, "mes": mes, "skills": skills, "sen": id_senioridade, "cargos": ids_cargo}).mappings().all()
    # só cargo: mesma estrutura de colunas do ranking_skills, com compatibilidade 100 (o cargo bate)
    return db.execute(text("""
        SELECT c.id AS id_colaborador, c.nome_abreviado AS nome_ficticio,
               coalesce(ds.descricao, ds.valor_dominio)::text AS senioridade,
               0::bigint AS skills_atendidas, 0::bigint AS skills_pedidas, 100::numeric AS score_percentual,
               d.total_alocado, d.disponibilidade
        FROM "InHire".colaboradores c
        JOIN "InHire".disponibilidade_mensal(:ano, :mes) d ON d.id_colaborador = c.id
        LEFT JOIN "InHire".dominios ds ON ds.id = c.id_senioridade
        WHERE c.status AND NOT c.deletado AND d.disponibilidade >= 1
          AND c.id_cargo = ANY(CAST(:cargos AS bigint[]))
          AND (CAST(:sen AS bigint) IS NULL OR c.id_senioridade = CAST(:sen AS bigint))
        ORDER BY d.disponibilidade DESC, c.nome_abreviado, c.id
    """), {"ano": ano, "mes": mes, "sen": id_senioridade, "cargos": ids_cargo}).mappings().all()


def _extrair_mes(prompt_norm: str, hoje: datetime.date) -> tuple[int, int, bool]:
    for indice, nome in enumerate(MESES_EXTENSO, start=1):
        if re.search(rf"\b{nome}\b", prompt_norm):
            ano = hoje.year + (1 if indice < hoje.month else 0)
            return ano, indice, True
    return hoje.year, hoje.month, False


def _extrair_senioridade(prompt_norm: str) -> Optional[str]:
    for chave, valor in SENIORIDADES.items():
        if re.search(rf"\b{chave}\b", prompt_norm):
            return valor
    return None


# ------------------------------------------------------------------ schemas da resposta
class BuscaIARequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)
    mes: Optional[int] = Field(default=None, ge=1, le=12)


class CriteriosExtraidos(BaseModel):
    skills: list[str]
    roles: list[str] = []
    seniority: Optional[str] = None
    urgency: str
    period: str


class Candidato(BaseModel):
    id: str
    name: str
    role: str
    source: Literal["INTERNO", "BANCO DE TALENTOS"]
    avatar: Optional[str] = None
    skills: list[str]
    engagement: int
    availability: int = 100  # % livre no mês (interno) ou disponibilidade informada (talento)
    freeDate: str
    currentProject: str
    matchScore: int
    reason: str


class BuscaIAResposta(BaseModel):
    extractedCriteria: CriteriosExtraidos
    hasAvailableInternal: bool
    candidates: list[Candidato]
    message: Optional[str] = None


# ------------------------------------------------------------------ POST /api/ia/buscar
@router.post("/ia/buscar", response_model=BuscaIAResposta)
def buscar_com_ia(dados: BuscaIARequest, db: Session = Depends(get_db)):
    hoje = _hoje()
    prompt_norm = _normalizar(dados.prompt)
    skills = _extrair_skills(db, prompt_norm)
    cargos = _extrair_cargos(db, prompt_norm)
    ids_cargo = [cid for cid, _ in cargos]
    nomes_cargo = [nome for _, nome in cargos]
    ano, mes, mes_citado = _extrair_mes(prompt_norm, hoje)
    if dados.ano and dados.mes:
        ano, mes, mes_citado = dados.ano, dados.mes, True
    senioridade = _extrair_senioridade(prompt_norm)
    imediato = bool(re.search(r"\b(agora|imediat\w*|urgente|asap)\b", prompt_norm))
    urgencia = "Imediata" if imediato else (f"A partir de {_mes_label(ano, mes)}" if mes_citado else "Flexível")

    criterios = CriteriosExtraidos(skills=skills, roles=nomes_cargo, seniority=senioridade, urgency=urgencia,
                                   period=_mes_label(ano, mes))
    if not skills and not cargos:
        return BuscaIAResposta(
            extractedCriteria=criterios, hasAvailableInternal=False, candidates=[],
            message="Não identifiquei nenhuma skill ou cargo cadastrado no texto. "
                    "Tente citar tecnologias (Python, React, Java, Figma) ou um cargo (Desenvolvedor, "
                    "Analista de Dados, Engenheiro de Soluções).",
        )

    id_senioridade = None
    if senioridade:
        id_senioridade = db.scalar(text(
            "SELECT id FROM \"InHire\".dominios WHERE tipo_dominio = 'SENIORIDADE' AND valor_dominio = :v"
        ), {"v": senioridade})

    # ---------------- 1) Banco Interno
    # Se o filtro não achar ninguém, relaxa primeiro a senioridade e depois o cargo (este só se houver skills).
    tentativas = [(id_senioridade, ids_cargo, None)]
    if id_senioridade:
        tentativas.append((None, ids_cargo, f"Nenhum profissional {senioridade} disponível; "
                                            f"mostrando outras senioridades."))
    if ids_cargo and skills:
        cargo_txt = " ou ".join(nomes_cargo)
        tentativas.append((id_senioridade, [], f"Nenhum {cargo_txt} disponível com essas skills; "
                                               f"mostrando outros cargos."))
        if id_senioridade:
            tentativas.append((None, [], f"Nenhum {cargo_txt} {senioridade} disponível com essas skills; "
                                         f"mostrando outros cargos e senioridades."))
    ranking, aviso = [], None
    for sen, cargos_filtro, mensagem in tentativas:
        ranking = _ranking_internos(db, ano, mes, skills, sen, cargos_filtro)
        if ranking:
            aviso = mensagem
            break
    internos = _selecionar_internos(ranking)

    ids = [r["id_colaborador"] for r in internos]
    cargos_colab = dict(db.execute(text("""
        SELECT c.id, d.valor_dominio FROM "InHire".colaboradores c
        JOIN "InHire".dominios d ON d.id = c.id_cargo WHERE c.id = ANY(CAST(:ids AS bigint[]))
    """), {"ids": ids}).all()) if ids else {}
    skills_lower = [s.lower() for s in skills]
    skills_por_colab: dict[int, list[str]] = {}
    if ids and skills:
        for r in db.execute(text("""
            SELECT DISTINCT cs.id_colaborador, s.nome_skill FROM "InHire".colaborador_skills cs
            JOIN "InHire".skills s ON s.id = cs.id_skill
            WHERE cs.id_colaborador = ANY(CAST(:ids AS bigint[])) AND cs.status AND NOT cs.deletado
              AND lower(s.nome_skill) = ANY(CAST(:sk AS text[]))
        """), {"ids": ids, "sk": skills_lower}):
            skills_por_colab.setdefault(r.id_colaborador, []).append(r.nome_skill)
    projetos = _projetos_atuais(db, ids, ano, mes)
    agenda = _disponibilidade_meses(db, ids, ano, mes, 12)

    candidatos: list[Candidato] = []
    for r in internos:
        cid = r["id_colaborador"]
        cargo = cargos_colab.get(cid, "Colaborador")
        disp = int(r["disponibilidade"])
        if skills:
            atendidas = sorted(skills_por_colab.get(cid, []), key=skills.index)
            motivo = (f"Atende {r['skills_atendidas']} de {r['skills_pedidas']} skills pedidas "
                      f"({', '.join(atendidas)}) e tem {disp}% de disponibilidade em {_mes_label(ano, mes)}.")
        else:
            atendidas = []
            motivo = f"Tem o cargo {cargo} e {disp}% de disponibilidade em {_mes_label(ano, mes)}."
        if r["senioridade"]:
            motivo += f" Senioridade: {r['senioridade']}."
        if disp < 100:
            motivo += f" Está parcialmente alocado(a) ({100 - disp}% ocupado no mês)."
        candidatos.append(Candidato(
            id=f"int-{cid}", name=r["nome_ficticio"], role=cargo,
            source="INTERNO", skills=atendidas, engagement=int(r["total_alocado"]), availability=disp,
            freeDate=_texto_liberacao(agenda.get(cid, [])),
            currentProject=projetos.get(cid) or "Nenhum (100% Livre)",
            matchScore=round(float(r["score_percentual"])), reason=motivo,
        ))

    # ---------------- 2) Banco de Talentos (acionado se faltar gente com match completo)
    match_completo = sum(1 for c in candidatos if c.matchScore == 100)
    if match_completo < MIN_MATCH_COMPLETO_INTERNO:
        talentos = _buscar_talentos(db, skills, skills_lower, id_senioridade, ids_cargo)
        if not talentos and ids_cargo and skills:  # mesmo relaxamento do Banco Interno
            talentos = _buscar_talentos(db, skills, skills_lower, id_senioridade, [])
            if talentos and not aviso:
                aviso = (f"Nenhum talento externo com o cargo {' ou '.join(nomes_cargo)} tem essas skills; "
                         f"mostrando outros cargos.")
        candidatos += talentos

    if not candidatos:
        aviso = "Nenhum profissional encontrado com esses critérios e disponibilidade."
    return BuscaIAResposta(extractedCriteria=criterios, hasAvailableInternal=bool(internos),
                           candidates=candidatos, message=aviso)


def _buscar_talentos(db: Session, skills: list[str], skills_lower: list[str], id_senioridade: Optional[int],
                     ids_cargo: list[int]) -> list[Candidato]:
    """Talentos externos com disponibilidade, filtrados por skills e/ou cargo."""
    filtros = """
        WHERE coalesce(t.disponibilidade_informada_percentual, 0) > 0
          AND (CAST(:sen AS bigint) IS NULL OR t.id_senioridade = CAST(:sen AS bigint))
          AND (cardinality(CAST(:cargos AS bigint[])) = 0 OR t.id_cargo = ANY(CAST(:cargos AS bigint[])))
    """
    params = {"sen": id_senioridade, "cargos": ids_cargo, "lim": LIMITE_TALENTOS}
    if skills:
        talentos = db.execute(text(f"""
            SELECT r.id_talento, r.nome_talento, r.skills_atendidas, r.skills_pedidas, r.score_percentual,
                   t.disponibilidade_informada_percentual AS disp, d.valor_dominio AS cargo
            FROM "InHire".ranking_talentos(CAST(:skills AS text[]), false) r
            JOIN "InHire".talentos t ON t.id = r.id_talento
            LEFT JOIN "InHire".dominios d ON d.id = t.id_cargo
            {filtros}
            ORDER BY r.score_percentual DESC, t.disponibilidade_informada_percentual DESC, r.id_talento
            LIMIT :lim
        """), {**params, "skills": skills}).mappings().all()
    else:
        talentos = db.execute(text(f"""
            SELECT t.id AS id_talento, t.nome_abreviado AS nome_talento, 0 AS skills_atendidas,
                   0 AS skills_pedidas, 100 AS score_percentual,
                   t.disponibilidade_informada_percentual AS disp, d.valor_dominio AS cargo
            FROM "InHire".talentos t
            LEFT JOIN "InHire".dominios d ON d.id = t.id_cargo
            {filtros} AND t.status
            ORDER BY t.disponibilidade_informada_percentual DESC, t.nome_abreviado, t.id
            LIMIT :lim
        """), params).mappings().all()

    tids = [t["id_talento"] for t in talentos]
    skills_por_talento: dict[int, list[str]] = {}
    if tids and skills:
        for r in db.execute(text("""
            SELECT DISTINCT ts.id_talento, s.nome_skill FROM "InHire".talento_skills ts
            JOIN "InHire".skills s ON s.id = ts.id_skill
            WHERE ts.id_talento = ANY(CAST(:ids AS bigint[])) AND lower(s.nome_skill) = ANY(CAST(:sk AS text[]))
        """), {"ids": tids, "sk": skills_lower}):
            skills_por_talento.setdefault(r.id_talento, []).append(r.nome_skill)

    resultado = []
    for t in talentos:
        disp = t["disp"] or 0
        cargo = t["cargo"] or "Profissional"
        if skills:
            atendidas = sorted(skills_por_talento.get(t["id_talento"], []), key=skills.index)
            motivo = (f"Perfil do Banco de Talentos que atende {t['skills_atendidas']} de "
                      f"{t['skills_pedidas']} skills ({', '.join(atendidas)}), com {disp}% de "
                      f"disponibilidade informada.")
        else:
            atendidas = []
            motivo = f"Perfil do Banco de Talentos com o cargo {cargo} e {disp}% de disponibilidade informada."
        resultado.append(Candidato(
            id=f"ext-{t['id_talento']}", name=t["nome_talento"], role=cargo,
            source="BANCO DE TALENTOS", skills=atendidas, engagement=0, availability=disp,
            freeDate="Imediato" if disp >= 100 else f"{disp}% de disponibilidade",
            currentProject="Mercado Externo", matchScore=round(float(t["score_percentual"])), reason=motivo,
        ))
    return resultado


# ------------------------------------------------------------------ GET /api/painel/projetos
class ProjetoCard(BaseModel):
    id: int
    name: str
    client: str
    status: str
    deadline: str
    progress: int
    teamSize: int


@router.get("/painel/projetos", response_model=list[ProjetoCard])
def painel_projetos(incluir_concluidos: bool = False, limit: int = Query(60, ge=1, le=300),
                    db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT d.id, d.nome_demanda, c.nome_contrato, a.valor_dominio AS andamento,
               d.dt_inicio_demanda, d.dt_termino_demanda_prevista,
               (SELECT count(*) FROM "InHire".alocacoes al
                WHERE al.id_demanda = d.id AND al.status AND NOT al.deletado) AS equipe
        FROM "InHire".demandas d
        JOIN "InHire".contratos c ON c.id = d.id_contrato
        JOIN "InHire".dominios a ON a.id = d.id_andamento_demanda
        WHERE d.status AND NOT d.deletado
          AND (:todos OR a.valor_dominio <> 'Concluída')
        ORDER BY d.dt_termino_demanda_prevista DESC, d.id
        LIMIT :lim
    """), {"todos": incluir_concluidos, "lim": limit}).all()

    hoje = _hoje()
    cards = []
    for r in rows:
        total = (r.dt_termino_demanda_prevista - r.dt_inicio_demanda).days or 1
        decorrido = (hoje - r.dt_inicio_demanda).days
        progresso = 100 if r.andamento == "Concluída" else max(0, min(100, round(decorrido * 100 / total)))
        cards.append(ProjetoCard(
            id=r.id, name=r.nome_demanda, client=r.nome_contrato, status=r.andamento,
            deadline=_data_label(r.dt_termino_demanda_prevista), progress=progresso, teamSize=r.equipe,
        ))
    return cards


# ------------------------------------------------------------------ GET /api/painel/equipes
class ColaboradorCard(BaseModel):
    id: int
    name: str
    role: str
    seniority: Optional[str] = None
    currentProject: str
    engagement: int
    freeDate: str
    avatar: Optional[str] = None
    # "livre" | "parcial" | "ocupado" | "sem_planejamento" (no mês atual)
    planningStatus: str
    # primeiro mês, nos próximos 6, sem nenhum planejamento lançado (ex.: "Dez/2026")
    unplannedFrom: Optional[str] = None


@router.get("/painel/equipes", response_model=list[ColaboradorCard])
def painel_equipes(nome: Optional[str] = None, apenas_disponiveis: bool = False,
                   limit: int = Query(60, ge=1, le=500), skip: int = Query(0, ge=0),
                   db: Session = Depends(get_db)):
    hoje = _hoje()
    rows = db.execute(text("""
        SELECT c.id, c.nome_abreviado, cg.valor_dominio AS cargo, sn.valor_dominio AS senioridade,
               d.total_alocado, d.disponibilidade
        FROM "InHire".colaboradores c
        JOIN "InHire".disponibilidade_mensal(:ano, :mes) d ON d.id_colaborador = c.id
        LEFT JOIN "InHire".dominios cg ON cg.id = c.id_cargo
        LEFT JOIN "InHire".dominios sn ON sn.id = c.id_senioridade AND sn.tipo_dominio = 'SENIORIDADE'
        WHERE c.status AND NOT c.deletado
          AND (CAST(:nome AS text) IS NULL OR c.nome_abreviado ILIKE '%' || CAST(:nome AS text) || '%')
          AND (NOT :disp OR d.disponibilidade > 0)
        ORDER BY d.disponibilidade DESC, c.nome_abreviado
        LIMIT :lim OFFSET :skip
    """), {"ano": hoje.year, "mes": hoje.month, "nome": nome, "disp": apenas_disponiveis,
           "lim": limit, "skip": skip}).all()

    ids = [r.id for r in rows]
    projetos = _projetos_atuais(db, ids, hoje.year, hoje.month)
    agenda = _disponibilidade_meses(db, ids, hoje.year, hoje.month, 12)
    planejados = _meses_planejados(db, ids, hoje.year, hoje.month, 6)
    cards = []
    for r in rows:
        situacao, lacuna = _situacao_planejamento(planejados.get(r.id, set()), hoje.year, hoje.month,
                                                  int(r.total_alocado))
        projeto = projetos.get(r.id) or (
            "Sem planejamento no mês" if situacao == "sem_planejamento" else "Nenhum (100% Livre)")
        cards.append(ColaboradorCard(
            id=r.id, name=r.nome_abreviado, role=r.cargo or "Colaborador", seniority=r.senioridade,
            currentProject=projeto, engagement=int(r.total_alocado),
            freeDate=_texto_liberacao(agenda.get(r.id, [])),
            planningStatus=situacao, unplannedFrom=lacuna,
        ))
    return cards


# ------------------------------------------------------------------ GET /api/painel/talentos
class TalentoCard(BaseModel):
    id: int
    name: str
    role: str
    seniority: Optional[str] = None
    skills: list[str]
    freeDate: str
    availability: int
    avatar: Optional[str] = None


@router.get("/painel/talentos", response_model=list[TalentoCard])
def painel_talentos(nome: Optional[str] = None, limit: int = Query(60, ge=1, le=500),
                    skip: int = Query(0, ge=0), db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT t.id, t.nome_abreviado, cg.valor_dominio AS cargo, sn.valor_dominio AS senioridade,
               coalesce(t.disponibilidade_informada_percentual, 0) AS disp,
               coalesce(array_agg(DISTINCT s.nome_skill) FILTER (WHERE s.id IS NOT NULL), '{}') AS skills
        FROM "InHire".talentos t
        LEFT JOIN "InHire".dominios cg ON cg.id = t.id_cargo
        LEFT JOIN "InHire".dominios sn ON sn.id = t.id_senioridade
        LEFT JOIN "InHire".talento_skills ts ON ts.id_talento = t.id
        LEFT JOIN "InHire".skills s ON s.id = ts.id_skill
        WHERE t.status
          AND (CAST(:nome AS text) IS NULL OR t.nome_abreviado ILIKE '%' || CAST(:nome AS text) || '%')
        GROUP BY t.id, cg.valor_dominio, sn.valor_dominio
        ORDER BY disp DESC, t.nome_abreviado
        LIMIT :lim OFFSET :skip
    """), {"nome": nome, "lim": limit, "skip": skip}).all()
    return [
        TalentoCard(
            id=r.id, name=r.nome_abreviado, role=r.cargo or "Profissional", seniority=r.senioridade,
            skills=list(r.skills), availability=r.disp,
            freeDate="Imediato" if r.disp >= 100 else (f"{r.disp}% disponível" if r.disp > 0 else "Indisponível"),
        )
        for r in rows
    ]
