from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Dominios, Skills
from app.schemas.schemas import DominioOut, SkillOut

router = APIRouter(prefix="/dominios", tags=["Domínios"])
skills_router = APIRouter(prefix="/skills", tags=["Skills"])


@router.get("/tipos", response_model=list[str])
def listar_tipos(db: Session = Depends(get_db)):
    """Lista os tipos de domínio existentes (CARGO, SENIORIDADE, MODALIDADE...)."""
    stmt = (
        select(Dominios.tipo_dominio)
        .where(Dominios.deletado.is_(False))
        .distinct()
        .order_by(Dominios.tipo_dominio)
    )
    return db.scalars(stmt).all()


@router.get("", response_model=list[DominioOut])
def listar_dominios(tipo: Optional[str] = None, apenas_ativos: bool = True, db: Session = Depends(get_db)):
    """Lista domínios. Ex.: /dominios?tipo=CARGO"""
    stmt = select(Dominios).where(Dominios.deletado.is_(False))
    if tipo:
        stmt = stmt.where(Dominios.tipo_dominio == tipo.upper())
    if apenas_ativos:
        stmt = stmt.where(Dominios.status.is_(True))
    return db.scalars(stmt.order_by(Dominios.tipo_dominio, Dominios.valor_dominio)).all()


@router.get("/{dominio_id}", response_model=DominioOut)
def obter_dominio(dominio_id: int, db: Session = Depends(get_db)):
    dominio = db.get(Dominios, dominio_id)
    if not dominio or dominio.deletado:
        raise HTTPException(404, "Domínio não encontrado")
    return dominio


@skills_router.get("", response_model=list[SkillOut])
def listar_skills(nome: Optional[str] = None, id_area: Optional[int] = None, db: Session = Depends(get_db)):
    """Lista skills ativas. Ex.: /skills?nome=java  ou  /skills?id_area=169"""
    stmt = select(Skills).where(Skills.status.is_(True), Skills.deletado.is_(False))
    if nome:
        stmt = stmt.where(Skills.nome_skill.ilike(f"%{nome}%"))
    if id_area:
        stmt = stmt.where(Skills.id_area_tecnologia == id_area)
    return db.scalars(stmt.order_by(Skills.nome_skill)).all()
