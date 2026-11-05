"""
Busca inteligente de profissionais.
Usa as funções que já existem no banco (schema "InHire"):
  buscar_profissionais, ranking_skills, ranking_talentos,
  disponibilidade_mensal e disponibilidade_periodo.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import DemandaSkills, Demandas, Skills
from app.schemas.schemas import (
    DisponibilidadeMensal,
    DisponibilidadePeriodo,
    ProfissionalBusca,
    RankingSkill,
    RankingTalento,
    SugestaoDemanda,
)

router = APIRouter(prefix="/busca", tags=["Busca inteligente"])

Ano = Annotated[int, Query(ge=1, le=9999, description="Ex.: 2026")]
Mes = Annotated[int, Query(ge=1, le=12, description="1 a 12")]


@router.get("/profissionais", response_model=list[ProfissionalBusca])
def buscar_profissionais(
    ano: Ano,
    mes: Mes,
    skills: list[int] = Query(default=[], description="IDs de skills que o profissional deve ter (todas)"),
    cargos: list[int] = Query(default=[], description="IDs de cargo aceitos"),
    id_senioridade: Optional[int] = None,
    disponibilidade_min: int = Query(0, le=100),
    db: Session = Depends(get_db),
):
    """Colaboradores ativos que têm TODAS as skills pedidas e disponibilidade mínima no mês."""
    sql = text(
        'SELECT * FROM "InHire".buscar_profissionais('
        ":ano, :mes, :senioridade, CAST(:skills AS bigint[]), :disp, CAST(:cargos AS bigint[]), NULL) "
        "ORDER BY disponibilidade DESC, nome_ficticio"
    )
    rows = db.execute(sql, {
        "ano": ano, "mes": mes, "senioridade": id_senioridade, "skills": skills,
        "disp": disponibilidade_min, "cargos": cargos or None,
    }).mappings().all()
    return rows


@router.get("/ranking-skills", response_model=list[RankingSkill])
def ranking_por_skills(
    ano: Ano,
    mes: Mes,
    skills: list[str] = Query(..., description="Nomes das skills. Ex.: skills=Java&skills=React"),
    disponibilidade_min: int = Query(0, ge=-1000, le=100),
    match_completo: bool = False,
    id_senioridade: Optional[int] = None,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Ranking de colaboradores pelo % de skills atendidas, depois pela disponibilidade."""
    sql = text(
        'SELECT * FROM "InHire".ranking_skills('
        ":ano, :mes, CAST(:skills AS text[]), :disp, :completo, :senioridade) LIMIT :limit"
    )
    return db.execute(sql, {
        "ano": ano, "mes": mes, "skills": skills, "disp": disponibilidade_min,
        "completo": match_completo, "senioridade": id_senioridade, "limit": limit,
    }).mappings().all()


@router.get("/ranking-talentos", response_model=list[RankingTalento])
def ranking_talentos(
    skills: list[str] = Query(..., description="Nomes das skills. Ex.: skills=Java&skills=React"),
    match_completo: bool = False,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Ranking do banco de talentos externos (candidatos) pelas skills pedidas."""
    sql = text(
        'SELECT * FROM "InHire".ranking_talentos(CAST(:skills AS text[]), :completo) LIMIT :limit'
    )
    return db.execute(sql, {"skills": skills, "completo": match_completo, "limit": limit}).mappings().all()


@router.get("/disponibilidade", response_model=list[DisponibilidadeMensal])
def disponibilidade_mensal(
    ano: Ano,
    mes: Mes,
    disponibilidade_min: int = Query(0, ge=-1000, le=100),
    db: Session = Depends(get_db),
):
    """Disponibilidade de cada colaborador ativo no mês (100 = livre; negativo = sobrealocado)."""
    sql = text(
        "SELECT d.id_colaborador, c.nome_abreviado, d.total_alocado, d.disponibilidade "
        'FROM "InHire".disponibilidade_mensal(:ano, :mes) d '
        'JOIN "InHire".colaboradores c ON c.id = d.id_colaborador '
        "WHERE c.status AND NOT c.deletado AND d.disponibilidade >= :disp "
        "ORDER BY d.disponibilidade DESC, c.nome_abreviado"
    )
    return db.execute(sql, {"ano": ano, "mes": mes, "disp": disponibilidade_min}).mappings().all()


@router.get("/disponibilidade-periodo", response_model=list[DisponibilidadePeriodo])
def disponibilidade_periodo(
    ano_inicio: Ano,
    mes_inicio: Mes,
    ano_fim: Ano,
    mes_fim: Mes,
    db: Session = Depends(get_db),
):
    """Resumo da disponibilidade de cada colaborador num período (máx. 61 meses)."""
    sql = text('SELECT * FROM "InHire".disponibilidade_periodo(:ai, :mi, :af, :mf)')
    return db.execute(sql, {"ai": ano_inicio, "mi": mes_inicio, "af": ano_fim, "mf": mes_fim}).mappings().all()


@router.get("/demandas/{demanda_id}/sugestoes", response_model=SugestaoDemanda)
def sugerir_para_demanda(
    demanda_id: int,
    ano: Ano,
    mes: Mes,
    disponibilidade_min: int = Query(1, ge=-1000, le=100),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Lê as skills exigidas pela demanda e sugere:
    - colaboradores internos (com disponibilidade no mês), e
    - talentos externos, caso falte gente interna.
    """
    demanda = db.get(Demandas, demanda_id)
    if not demanda or demanda.deletado:
        raise HTTPException(404, "Demanda não encontrada")

    nomes_skills = db.scalars(
        select(Skills.nome_skill)
        .join(DemandaSkills, DemandaSkills.id_skill == Skills.id)
        .where(DemandaSkills.id_demanda == demanda_id, DemandaSkills.status.is_(True), DemandaSkills.deletado.is_(False))
        .order_by(Skills.nome_skill)
    ).all()
    if not nomes_skills:
        raise HTTPException(400, "Essa demanda não tem skills cadastradas. Use PUT /demandas/{id}/skills")

    colaboradores = ranking_por_skills(
        ano=ano, mes=mes, skills=nomes_skills, disponibilidade_min=disponibilidade_min,
        match_completo=False, id_senioridade=None, limit=limit, db=db,
    )
    talentos = ranking_talentos(skills=nomes_skills, match_completo=False, limit=limit, db=db)
    return SugestaoDemanda(
        demanda=demanda.nome_demanda,
        skills_exigidas=nomes_skills,
        colaboradores=colaboradores,
        talentos_externos=talentos,
    )
