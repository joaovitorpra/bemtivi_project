"""
Página Utilização do TalentFlow: mostra quanto da capacidade da equipe está sendo
usada e sugere onde encaixar quem tem horas livres.

  GET  /api/utilizacao/indicadores    -> indicadores do mês + evolução dos próximos meses
  GET  /api/utilizacao/oportunidades  -> pessoas com horas livres e demandas sugeridas
  POST /api/utilizacao/alocar         -> aloca de verdade (alocação + planejamento do mês)

Regras de cálculo:
- Jornada de HORAS_MES horas por mês.
- Ocupação de uma pessoa no mês = soma das porcentagens planejadas, limitada a 100%.
- "Sem planejamento" = colaborador ativo sem nenhum planejamento lançado no mês.
  Essas pessoas NÃO entram na ocupação média nem nas horas ociosas, porque não dá
  para saber se estão livres ou se o gestor só não lançou. Elas aparecem num
  indicador separado.
- Sugestões de encaixe: demandas ativas (não concluídas, vigentes no mês) que
  exigem skills que a pessoa tem, ordenadas pela % das skills exigidas que ela cobre.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.alocacoes import gravar_planejamento, ocupacao_no_mes, validar_sobrealocacao
from app.api.talentflow import MESES, _hoje, _mes_label, _projetos_atuais, _proximos_meses
from app.core.database import get_db
from app.models.models import Alocacoes, Colaboradores, Demandas

router = APIRouter(prefix="/api/utilizacao", tags=["Frontend (TalentFlow)"])

HORAS_MES = 160  # jornada mensal usada para converter % em horas
ANDAMENTOS_ENCERRADOS = ["Concluída", "Cancelada"]  # demandas nesses andamentos não recebem sugestões


def _horas(porcentagem: float) -> int:
    return round(porcentagem * HORAS_MES / 100)


def _mes_referencia(ano: Optional[int], mes: Optional[int]) -> tuple[int, int]:
    if ano and mes:
        return ano, mes
    hoje = _hoje()
    return hoje.year, hoje.month


# ------------------------------------------------------------------ GET /api/utilizacao/indicadores
class MesUtilizacao(BaseModel):
    period: str               # "Nov/2026"
    ano: int
    mes: int
    plannedEmployees: int     # pessoas com planejamento lançado no mês
    averageOccupancy: float   # ocupação média (%) de quem tem planejamento
    fullyAllocated: int       # 100% ocupados
    partial: int              # entre 1% e 99%
    free: int                 # planejamento lançado com 0%
    unplanned: int            # sem nenhum planejamento no mês
    idleHours: int            # horas livres de quem tem planejamento
    idleFte: float            # horas ociosas convertidas em "pessoas inteiras"


class IndicadoresResposta(BaseModel):
    hoursPerMonth: int
    totalEmployees: int
    current: MesUtilizacao
    trend: list[MesUtilizacao]


@router.get("/indicadores", response_model=IndicadoresResposta)
def indicadores(ano: Optional[int] = Query(None, ge=2000, le=2100), mes: Optional[int] = Query(None, ge=1, le=12),
                meses: int = Query(6, ge=1, le=12), db: Session = Depends(get_db)):
    ano, mes = _mes_referencia(ano, mes)
    periodo = _proximos_meses(ano, mes, meses)

    total = db.scalar(text(
        'SELECT count(*) FROM "InHire".colaboradores WHERE status AND NOT deletado'
    ))
    rows = db.execute(text("""
        WITH m AS (
            SELECT * FROM unnest(CAST(:anos AS int[]), CAST(:meses AS text[]))
                   WITH ORDINALITY AS m(ano, mes, ordem)
        ),
        plano AS (
            SELECT p.ano, p.mes, a.id_colaborador, LEAST(sum(p.porcentagem), 100) AS ocupacao
            FROM "InHire".planejamentos p
            JOIN "InHire".alocacoes a ON a.id = p.id_alocacao
            JOIN "InHire".colaboradores c ON c.id = a.id_colaborador
            JOIN m ON m.ano = p.ano AND m.mes = p.mes
            WHERE p.status AND NOT p.deletado AND a.status AND NOT a.deletado
              AND c.status AND NOT c.deletado
            GROUP BY p.ano, p.mes, a.id_colaborador
        )
        SELECT m.ordem, m.ano, m.mes,
               count(plano.id_colaborador)                                   AS planejados,
               coalesce(avg(plano.ocupacao), 0)                               AS ocupacao_media,
               count(*) FILTER (WHERE plano.ocupacao >= 100)                  AS ocupados,
               count(*) FILTER (WHERE plano.ocupacao > 0 AND plano.ocupacao < 100) AS parciais,
               count(*) FILTER (WHERE plano.ocupacao = 0)                     AS livres,
               coalesce(sum(100 - plano.ocupacao), 0)                         AS pct_ocioso
        FROM m LEFT JOIN plano ON plano.ano = m.ano AND plano.mes = m.mes
        GROUP BY m.ordem, m.ano, m.mes
        ORDER BY m.ordem
    """), {"anos": [a for a, _ in periodo], "meses": [MESES[m - 1] for _, m in periodo]}).all()

    tendencia = []
    for (a, m), r in zip(periodo, rows):
        horas = _horas(float(r.pct_ocioso))
        tendencia.append(MesUtilizacao(
            period=_mes_label(a, m), ano=a, mes=m, plannedEmployees=r.planejados,
            averageOccupancy=round(float(r.ocupacao_media), 1), fullyAllocated=r.ocupados,
            partial=r.parciais, free=r.livres, unplanned=total - r.planejados,
            idleHours=horas, idleFte=round(horas / HORAS_MES, 1),
        ))
    return IndicadoresResposta(hoursPerMonth=HORAS_MES, totalEmployees=total,
                               current=tendencia[0], trend=tendencia)


# ------------------------------------------------------------------ GET /api/utilizacao/oportunidades
class SugestaoEncaixe(BaseModel):
    demandId: int
    demandName: str
    client: str
    matchScore: int            # % das skills exigidas pela demanda que a pessoa tem
    matchedSkills: list[str]
    requiredSkills: int
    suggestedPercent: int      # quanto dá para alocar sem passar de 100%


class Oportunidade(BaseModel):
    id: int
    name: str
    role: str
    seniority: Optional[str] = None
    occupancy: int
    freePercent: int
    freeHours: int
    currentProject: str
    suggestions: list[SugestaoEncaixe]


class OportunidadesResposta(BaseModel):
    period: str
    ano: int
    mes: int
    hoursPerMonth: int
    opportunities: list[Oportunidade]


def _sugestoes(db: Session, ids: list[int], ano: int, mes: int, limite: int,
               id_demanda: Optional[int]) -> dict[int, list[dict]]:
    """Demandas vigentes no mês que pedem skills que cada pessoa tem (sem as que ela já está)."""
    if not ids:
        return {}
    inicio_mes = f"{ano:04d}-{mes:02d}-01"
    rows = db.execute(text("""
        WITH dem AS (
            SELECT d.id, d.nome_demanda, ct.nome_contrato
            FROM "InHire".demandas d
            JOIN "InHire".contratos ct ON ct.id = d.id_contrato
            JOIN "InHire".dominios an ON an.id = d.id_andamento_demanda
            WHERE d.status AND NOT d.deletado AND an.valor_dominio <> ALL(CAST(:encerrados AS text[]))
              AND d.dt_inicio_demanda < CAST(:inicio AS date) + interval '1 month'
              AND d.dt_termino_demanda_prevista >= CAST(:inicio AS date)
              AND (CAST(:id_demanda AS bigint) IS NULL OR d.id = CAST(:id_demanda AS bigint))
        ),
        exigidas AS (
            SELECT DISTINCT ds.id_demanda, ds.id_skill
            FROM "InHire".demanda_skills ds JOIN dem ON dem.id = ds.id_demanda
            WHERE ds.status AND NOT ds.deletado
        ),
        total AS (SELECT id_demanda, count(*) AS n FROM exigidas GROUP BY id_demanda),
        atende AS (
            SELECT cs.id_colaborador, e.id_demanda, count(DISTINCT e.id_skill) AS n_ok,
                   array_agg(DISTINCT s.nome_skill ORDER BY s.nome_skill) AS skills
            FROM "InHire".colaborador_skills cs
            JOIN exigidas e ON e.id_skill = cs.id_skill
            JOIN "InHire".skills s ON s.id = e.id_skill
            WHERE cs.id_colaborador = ANY(CAST(:ids AS bigint[])) AND cs.status AND NOT cs.deletado
            GROUP BY cs.id_colaborador, e.id_demanda
        ),
        ranking AS (
            SELECT at.*, t.n,
                   row_number() OVER (PARTITION BY at.id_colaborador
                                      ORDER BY at.n_ok::numeric / t.n DESC, at.n_ok DESC, at.id_demanda) AS pos
            FROM atende at JOIN total t ON t.id_demanda = at.id_demanda
            WHERE NOT EXISTS (
                SELECT 1 FROM "InHire".alocacoes al
                WHERE al.id_colaborador = at.id_colaborador AND al.id_demanda = at.id_demanda
                  AND al.status AND NOT al.deletado
            )
        )
        SELECT r.id_colaborador, r.id_demanda, r.n_ok, r.n, r.skills, dem.nome_demanda, dem.nome_contrato
        FROM ranking r JOIN dem ON dem.id = r.id_demanda
        WHERE r.pos <= :limite
        ORDER BY r.id_colaborador, r.pos
    """), {"inicio": inicio_mes, "ids": ids, "limite": limite, "id_demanda": id_demanda,
          "encerrados": ANDAMENTOS_ENCERRADOS}).all()
    resultado: dict[int, list[dict]] = {}
    for r in rows:
        resultado.setdefault(r.id_colaborador, []).append({
            "demandId": r.id_demanda, "demandName": r.nome_demanda, "client": r.nome_contrato,
            "matchScore": round(r.n_ok * 100 / r.n), "matchedSkills": list(r.skills),
            "requiredSkills": r.n,
        })
    return resultado


@router.get("/oportunidades", response_model=OportunidadesResposta)
def oportunidades(ano: Optional[int] = Query(None, ge=2000, le=2100), mes: Optional[int] = Query(None, ge=1, le=12),
                  sugestoes: int = Query(3, ge=1, le=10), limit: int = Query(30, ge=1, le=200),
                  id_demanda: Optional[int] = Query(None, description="Só sugere encaixes nesta demanda"),
                  apenas_com_sugestao: bool = False, db: Session = Depends(get_db)):
    """Pessoas com planejamento lançado e horas livres no mês (as mais livres primeiro)."""
    ano, mes = _mes_referencia(ano, mes)
    pessoas = db.execute(text("""
        SELECT c.id, c.nome_abreviado, cg.valor_dominio AS cargo, sn.valor_dominio AS senioridade,
               LEAST(sum(p.porcentagem), 100) AS ocupacao
        FROM "InHire".colaboradores c
        JOIN "InHire".alocacoes a ON a.id_colaborador = c.id AND a.status AND NOT a.deletado
        JOIN "InHire".planejamentos p ON p.id_alocacao = a.id AND p.status AND NOT p.deletado
             AND p.ano = :ano AND p.mes = :mes
        LEFT JOIN "InHire".dominios cg ON cg.id = c.id_cargo
        LEFT JOIN "InHire".dominios sn ON sn.id = c.id_senioridade AND sn.tipo_dominio = 'SENIORIDADE'
        WHERE c.status AND NOT c.deletado
        GROUP BY c.id, c.nome_abreviado, cg.valor_dominio, sn.valor_dominio
        HAVING sum(p.porcentagem) < 100
        ORDER BY ocupacao, c.nome_abreviado
    """), {"ano": ano, "mes": MESES[mes - 1]}).all()

    ids = [p.id for p in pessoas]
    encaixes = _sugestoes(db, ids, ano, mes, sugestoes, id_demanda)
    if apenas_com_sugestao or id_demanda:
        pessoas = [p for p in pessoas if encaixes.get(p.id)]
    pessoas = pessoas[:limit]
    projetos = _projetos_atuais(db, [p.id for p in pessoas], ano, mes)

    lista = []
    for p in pessoas:
        livre = 100 - int(p.ocupacao)
        lista.append(Oportunidade(
            id=p.id, name=p.nome_abreviado, role=p.cargo or "Colaborador", seniority=p.senioridade,
            occupancy=int(p.ocupacao), freePercent=livre, freeHours=_horas(livre),
            currentProject=projetos.get(p.id) or "Nenhum (100% Livre)",
            suggestions=[SugestaoEncaixe(**s, suggestedPercent=livre) for s in encaixes.get(p.id, [])],
        ))
    return OportunidadesResposta(period=_mes_label(ano, mes), ano=ano, mes=mes,
                                 hoursPerMonth=HORAS_MES, opportunities=lista)


# ------------------------------------------------------------------ POST /api/utilizacao/alocar
class AlocarRequest(BaseModel):
    id_colaborador: int
    id_demanda: int
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    porcentagem: int = Field(ge=1, le=100)


class AlocarResposta(BaseModel):
    allocationId: int
    createdAllocation: bool    # false = a pessoa já estava na demanda e só o mês foi atualizado
    period: str
    percent: int
    occupancyBefore: int
    occupancyAfter: int
    message: str


@router.post("/alocar", response_model=AlocarResposta, status_code=status.HTTP_201_CREATED)
def alocar(dados: AlocarRequest, db: Session = Depends(get_db)):
    """
    Aloca o colaborador na demanda e lança a % no mês, numa única transação.
    Usa a mesma regra de sobrealocação de PUT /alocacoes/{id}/planejamentos:
    se passar de 100%, nada é gravado.
    """
    colab = db.get(Colaboradores, dados.id_colaborador)
    if not colab or colab.deletado or not colab.status:
        raise HTTPException(404, "Colaborador não encontrado ou inativo")
    demanda = db.get(Demandas, dados.id_demanda)
    if not demanda or demanda.deletado or not demanda.status:
        raise HTTPException(404, "Demanda não encontrada ou inativa")

    mes_nome = MESES[dados.mes - 1]
    alocacao = db.scalar(select(Alocacoes).where(
        Alocacoes.id_colaborador == dados.id_colaborador,
        Alocacoes.id_demanda == dados.id_demanda,
        Alocacoes.status.is_(True),
        Alocacoes.deletado.is_(False),
    ))
    ocupacao_antes = ocupacao_no_mes(db, dados.id_colaborador, mes_nome, dados.ano)
    ocupado_em_outras = ocupacao_no_mes(db, dados.id_colaborador, mes_nome, dados.ano,
                                        ignorar_alocacao=alocacao.id if alocacao else None)
    validar_sobrealocacao(ocupado_em_outras, dados.porcentagem, mes_nome, dados.ano)

    criada = alocacao is None
    if criada:
        alocacao = Alocacoes(id_colaborador=dados.id_colaborador, id_demanda=dados.id_demanda)
        db.add(alocacao)
        db.flush()  # gera o id sem gravar ainda
    gravar_planejamento(db, alocacao.id, mes_nome, dados.ano, dados.porcentagem)
    db.commit()

    depois = ocupado_em_outras + dados.porcentagem
    periodo = _mes_label(dados.ano, dados.mes)
    return AlocarResposta(
        allocationId=alocacao.id, createdAllocation=criada, period=periodo, percent=dados.porcentagem,
        occupancyBefore=min(ocupacao_antes, 100), occupancyAfter=depois,
        message=f"{colab.nome_abreviado} alocado(a) em {demanda.nome_demanda} com {dados.porcentagem}% "
                f"em {periodo}. Ocupação no mês: {depois}%.",
    )
