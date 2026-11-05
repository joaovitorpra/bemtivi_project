from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Alocacoes, Colaboradores, Demandas, Planejamentos
from app.schemas.schemas import (
    AlocacaoCreate,
    AlocacaoDetalhe,
    AlocacaoOut,
    PlanejamentoIn,
    PlanejamentoOut,
)

router = APIRouter(prefix="/alocacoes", tags=["Alocações"])


def _buscar(db: Session, alocacao_id: int) -> Alocacoes:
    alocacao = db.get(Alocacoes, alocacao_id)
    if not alocacao or alocacao.deletado:
        raise HTTPException(404, "Alocação não encontrada")
    return alocacao


def _planejamentos(db: Session, alocacao_id: int) -> list[Planejamentos]:
    return db.scalars(
        select(Planejamentos)
        .where(Planejamentos.id_alocacao == alocacao_id, Planejamentos.deletado.is_(False))
        .order_by(Planejamentos.ano, Planejamentos.id)
    ).all()


@router.get("", response_model=list[AlocacaoOut])
def listar_alocacoes(
    id_colaborador: Optional[int] = None,
    id_demanda: Optional[int] = None,
    apenas_ativas: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Alocacoes).where(Alocacoes.deletado.is_(False))
    if apenas_ativas:
        stmt = stmt.where(Alocacoes.status.is_(True))
    if id_colaborador:
        stmt = stmt.where(Alocacoes.id_colaborador == id_colaborador)
    if id_demanda:
        stmt = stmt.where(Alocacoes.id_demanda == id_demanda)
    return db.scalars(stmt.order_by(Alocacoes.id).offset(skip).limit(limit)).all()


@router.get("/{alocacao_id}", response_model=AlocacaoDetalhe)
def obter_alocacao(alocacao_id: int, db: Session = Depends(get_db)):
    alocacao = _buscar(db, alocacao_id)
    detalhe = AlocacaoDetalhe.model_validate(alocacao)
    detalhe.planejamentos = [PlanejamentoOut.model_validate(p) for p in _planejamentos(db, alocacao_id)]
    return detalhe


@router.post("", response_model=AlocacaoOut, status_code=status.HTTP_201_CREATED)
def criar_alocacao(dados: AlocacaoCreate, db: Session = Depends(get_db)):
    colab = db.get(Colaboradores, dados.id_colaborador)
    if not colab or colab.deletado or not colab.status:
        raise HTTPException(404, "Colaborador não encontrado ou inativo")
    demanda = db.get(Demandas, dados.id_demanda)
    if not demanda or demanda.deletado or not demanda.status:
        raise HTTPException(404, "Demanda não encontrada ou inativa")

    ja_existe = db.scalar(
        select(Alocacoes.id).where(
            Alocacoes.id_colaborador == dados.id_colaborador,
            Alocacoes.id_demanda == dados.id_demanda,
            Alocacoes.status.is_(True),
            Alocacoes.deletado.is_(False),
        )
    )
    if ja_existe:
        raise HTTPException(409, f"O colaborador já está alocado nessa demanda (alocação {ja_existe})")

    alocacao = Alocacoes(**dados.model_dump())
    db.add(alocacao)
    db.commit()
    db.refresh(alocacao)
    return alocacao


@router.delete("/{alocacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_alocacao(alocacao_id: int, db: Session = Depends(get_db)):
    """Exclusão lógica da alocação (os planejamentos deixam de contar na disponibilidade)."""
    alocacao = _buscar(db, alocacao_id)
    alocacao.deletado = True
    alocacao.status = False
    db.commit()


# ---------------------------------------------------------------- Planejamento mensal
def ocupacao_no_mes(db: Session, id_colaborador: int, mes: str, ano: int,
                    ignorar_alocacao: Optional[int] = None) -> int:
    """Soma da % planejada do colaborador no mês, nas alocações ativas (exceto `ignorar_alocacao`)."""
    stmt = (
        select(func.coalesce(func.sum(Planejamentos.porcentagem), 0))
        .join(Alocacoes, Alocacoes.id == Planejamentos.id_alocacao)
        .where(
            Alocacoes.id_colaborador == id_colaborador,
            Alocacoes.status.is_(True),
            Alocacoes.deletado.is_(False),
            Planejamentos.mes == mes,
            Planejamentos.ano == ano,
            Planejamentos.status.is_(True),
            Planejamentos.deletado.is_(False),
        )
    )
    if ignorar_alocacao is not None:
        stmt = stmt.where(Alocacoes.id != ignorar_alocacao)
    return int(db.scalar(stmt))


def validar_sobrealocacao(ocupado_em_outras: int, porcentagem: int, mes: str, ano: int) -> None:
    """Regra de negócio: a soma das alocações do colaborador no mês não pode passar de 100%."""
    if ocupado_em_outras + porcentagem > 100:
        raise HTTPException(
            409,
            f"Sobrealocação: o colaborador já tem {ocupado_em_outras}% em {mes}/{ano}. "
            f"Máximo disponível: {100 - ocupado_em_outras}%",
        )


def gravar_planejamento(db: Session, alocacao_id: int, mes: str, ano: int, porcentagem: int) -> Planejamentos:
    """Cria ou atualiza o planejamento do mês (sem commit; quem chama decide quando gravar)."""
    planejamento = db.scalar(
        select(Planejamentos).where(
            Planejamentos.id_alocacao == alocacao_id,
            Planejamentos.mes == mes,
            Planejamentos.ano == ano,
        )
    )
    if planejamento:
        planejamento.porcentagem = porcentagem
        planejamento.status = True
        planejamento.deletado = False
    else:
        planejamento = Planejamentos(id_alocacao=alocacao_id, mes=mes, ano=ano, porcentagem=porcentagem)
        db.add(planejamento)
    return planejamento


@router.put("/{alocacao_id}/planejamentos", response_model=PlanejamentoOut)
def definir_planejamento(alocacao_id: int, dados: PlanejamentoIn, db: Session = Depends(get_db)):
    """
    Define a porcentagem de dedicação num mês (cria ou atualiza).
    Bloqueia se a soma das alocações do colaborador no mês passar de 100%.
    """
    alocacao = _buscar(db, alocacao_id)
    ocupado = ocupacao_no_mes(db, alocacao.id_colaborador, dados.mes, dados.ano, ignorar_alocacao=alocacao_id)
    validar_sobrealocacao(ocupado, dados.porcentagem, dados.mes, dados.ano)

    planejamento = gravar_planejamento(db, alocacao_id, dados.mes, dados.ano, dados.porcentagem)
    db.commit()
    db.refresh(planejamento)
    return planejamento


@router.get("/{alocacao_id}/planejamentos", response_model=list[PlanejamentoOut])
def listar_planejamentos(alocacao_id: int, db: Session = Depends(get_db)):
    _buscar(db, alocacao_id)
    return _planejamentos(db, alocacao_id)
