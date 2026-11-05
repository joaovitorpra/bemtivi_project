from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Colaboradores, Contratos, Demandas
from app.schemas.schemas import ColaboradorOut, ContratoOut, DemandaOut

router = APIRouter(prefix="/contratos", tags=["Contratos"])


def _buscar(db: Session, contrato_id: int) -> Contratos:
    contrato = db.get(Contratos, contrato_id)
    if not contrato or contrato.deletado:
        raise HTTPException(404, "Contrato não encontrado")
    return contrato


@router.get("", response_model=list[ContratoOut])
def listar_contratos(apenas_ativos: bool = True, db: Session = Depends(get_db)):
    stmt = select(Contratos).where(Contratos.deletado.is_(False))
    if apenas_ativos:
        stmt = stmt.where(Contratos.status.is_(True))
    return db.scalars(stmt.order_by(Contratos.id)).all()


@router.get("/{contrato_id}", response_model=ContratoOut)
def obter_contrato(contrato_id: int, db: Session = Depends(get_db)):
    return _buscar(db, contrato_id)


@router.get("/{contrato_id}/demandas", response_model=list[DemandaOut])
def demandas_do_contrato(contrato_id: int, db: Session = Depends(get_db)):
    _buscar(db, contrato_id)
    stmt = select(Demandas).where(Demandas.id_contrato == contrato_id, Demandas.deletado.is_(False))
    return db.scalars(stmt.order_by(Demandas.id)).all()


@router.get("/{contrato_id}/colaboradores", response_model=list[ColaboradorOut])
def colaboradores_do_contrato(contrato_id: int, db: Session = Depends(get_db)):
    _buscar(db, contrato_id)
    stmt = select(Colaboradores).where(
        Colaboradores.id_contrato == contrato_id, Colaboradores.deletado.is_(False)
    )
    return db.scalars(stmt.order_by(Colaboradores.nome_abreviado)).all()
