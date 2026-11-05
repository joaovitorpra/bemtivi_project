from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Skills, TalentoSkills, Talentos
from app.schemas.schemas import SkillOut, TalentoDetalhe, TalentoOut

router = APIRouter(prefix="/talentos", tags=["Talentos (banco externo)"])


@router.get("", response_model=list[TalentoOut])
def listar_talentos(
    nome: Optional[str] = None,
    id_senioridade: Optional[int] = None,
    disponibilidade_min: int = Query(0, ge=0, le=100),
    apenas_ativos: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Talentos)
    if apenas_ativos:
        stmt = stmt.where(Talentos.status.is_(True))
    if nome:
        stmt = stmt.where(Talentos.nome_abreviado.ilike(f"%{nome}%"))
    if id_senioridade:
        stmt = stmt.where(Talentos.id_senioridade == id_senioridade)
    if disponibilidade_min:
        stmt = stmt.where(Talentos.disponibilidade_informada_percentual >= disponibilidade_min)
    return db.scalars(stmt.order_by(Talentos.nome_abreviado).offset(skip).limit(limit)).all()


@router.get("/{talento_id}", response_model=TalentoDetalhe)
def obter_talento(talento_id: int, db: Session = Depends(get_db)):
    talento = db.get(Talentos, talento_id)
    if not talento:
        raise HTTPException(404, "Talento não encontrado")
    skills = db.scalars(
        select(Skills)
        .join(TalentoSkills, TalentoSkills.id_skill == Skills.id)
        .where(TalentoSkills.id_talento == talento_id)
        .order_by(Skills.nome_skill)
    ).all()
    detalhe = TalentoDetalhe.model_validate(talento)
    detalhe.skills = [SkillOut.model_validate(s) for s in skills]
    return detalhe
