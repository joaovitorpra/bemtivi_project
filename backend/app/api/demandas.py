from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Alocacoes, DemandaSkills, Demandas, Skills
from app.schemas.schemas import (
    AlocacaoOut,
    DemandaCreate,
    DemandaDetalhe,
    DemandaOut,
    DemandaUpdate,
    SkillOut,
)

router = APIRouter(prefix="/demandas", tags=["Demandas"])


def _buscar(db: Session, demanda_id: int) -> Demandas:
    demanda = db.get(Demandas, demanda_id)
    if not demanda or demanda.deletado:
        raise HTTPException(404, "Demanda não encontrada")
    return demanda


def _skills_da_demanda(db: Session, demanda_id: int) -> list[Skills]:
    return db.scalars(
        select(Skills)
        .join(DemandaSkills, DemandaSkills.id_skill == Skills.id)
        .where(
            DemandaSkills.id_demanda == demanda_id,
            DemandaSkills.status.is_(True),
            DemandaSkills.deletado.is_(False),
        )
        .order_by(Skills.nome_skill)
    ).all()


def _validar_skills(db: Session, ids: list[int]) -> list[int]:
    ids = list(dict.fromkeys(ids))  # remove repetidos mantendo a ordem
    if not ids:
        return ids
    encontrados = set(db.scalars(select(Skills.id).where(Skills.id.in_(ids), Skills.deletado.is_(False))))
    faltando = [i for i in ids if i not in encontrados]
    if faltando:
        raise HTTPException(400, f"Skills inexistentes: {faltando}")
    return ids


@router.get("", response_model=list[DemandaOut])
def listar_demandas(
    nome: Optional[str] = None,
    id_contrato: Optional[int] = None,
    id_andamento: Optional[int] = None,
    apenas_ativas: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Demandas).where(Demandas.deletado.is_(False))
    if apenas_ativas:
        stmt = stmt.where(Demandas.status.is_(True))
    if nome:
        stmt = stmt.where(Demandas.nome_demanda.ilike(f"%{nome}%"))
    if id_contrato:
        stmt = stmt.where(Demandas.id_contrato == id_contrato)
    if id_andamento:
        stmt = stmt.where(Demandas.id_andamento_demanda == id_andamento)
    return db.scalars(stmt.order_by(Demandas.id).offset(skip).limit(limit)).all()


@router.get("/{demanda_id}", response_model=DemandaDetalhe)
def obter_demanda(demanda_id: int, db: Session = Depends(get_db)):
    demanda = _buscar(db, demanda_id)
    detalhe = DemandaDetalhe.model_validate(demanda)
    detalhe.skills = [SkillOut.model_validate(s) for s in _skills_da_demanda(db, demanda_id)]
    return detalhe


@router.post("", response_model=DemandaDetalhe, status_code=status.HTTP_201_CREATED)
def criar_demanda(dados: DemandaCreate, db: Session = Depends(get_db)):
    skills = _validar_skills(db, dados.skills)
    demanda = Demandas(**dados.model_dump(exclude={"skills"}))
    db.add(demanda)
    db.flush()  # gera o id da demanda
    for id_skill in skills:
        db.add(DemandaSkills(id_demanda=demanda.id, id_skill=id_skill))
    db.commit()
    return obter_demanda(demanda.id, db)


@router.patch("/{demanda_id}", response_model=DemandaOut)
def atualizar_demanda(demanda_id: int, dados: DemandaUpdate, db: Session = Depends(get_db)):
    demanda = _buscar(db, demanda_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(demanda, campo, valor)
    if demanda.dt_termino_demanda_prevista < demanda.dt_inicio_demanda:
        db.rollback()
        raise HTTPException(422, "dt_termino_demanda_prevista deve ser maior ou igual a dt_inicio_demanda")
    db.commit()
    db.refresh(demanda)
    return demanda


@router.delete("/{demanda_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_demanda(demanda_id: int, db: Session = Depends(get_db)):
    """Exclusão lógica da demanda."""
    demanda = _buscar(db, demanda_id)
    demanda.deletado = True
    demanda.status = False
    db.commit()


@router.put("/{demanda_id}/skills", response_model=list[SkillOut])
def definir_skills(demanda_id: int, skills: list[int], db: Session = Depends(get_db)):
    """Substitui a lista de skills exigidas pela demanda. Corpo: [16, 59, 41]"""
    _buscar(db, demanda_id)
    novas = set(_validar_skills(db, skills))
    atuais = db.scalars(
        select(DemandaSkills).where(DemandaSkills.id_demanda == demanda_id, DemandaSkills.deletado.is_(False))
    ).all()
    for registro in atuais:
        if registro.id_skill in novas:
            registro.status = True
            novas.discard(registro.id_skill)
        else:
            registro.deletado = True
            registro.status = False
    for id_skill in novas:
        db.add(DemandaSkills(id_demanda=demanda_id, id_skill=id_skill))
    db.commit()
    return [SkillOut.model_validate(s) for s in _skills_da_demanda(db, demanda_id)]


@router.get("/{demanda_id}/alocacoes", response_model=list[AlocacaoOut])
def alocacoes_da_demanda(demanda_id: int, db: Session = Depends(get_db)):
    _buscar(db, demanda_id)
    stmt = select(Alocacoes).where(Alocacoes.id_demanda == demanda_id, Alocacoes.deletado.is_(False))
    return db.scalars(stmt.order_by(Alocacoes.id)).all()
