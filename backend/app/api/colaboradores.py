from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import ColaboradorSkills, Colaboradores, Dominios, Skills
from app.schemas.schemas import (
    ColaboradorCreate,
    ColaboradorDetalhe,
    ColaboradorOut,
    ColaboradorSkillIn,
    ColaboradorSkillOut,
    ColaboradorUpdate,
)

router = APIRouter(prefix="/colaboradores", tags=["Colaboradores"])


def _buscar_ativo(db: Session, colaborador_id: int) -> Colaboradores:
    colab = db.get(Colaboradores, colaborador_id)
    if not colab or colab.deletado:
        raise HTTPException(404, "Colaborador não encontrado")
    return colab


def _skills_do_colaborador(db: Session, colaborador_id: int) -> list[ColaboradorSkillOut]:
    stmt = (
        select(ColaboradorSkills.id, ColaboradorSkills.id_skill, Skills.nome_skill, ColaboradorSkills.nivel_conhecimento)
        .join(Skills, Skills.id == ColaboradorSkills.id_skill)
        .where(
            ColaboradorSkills.id_colaborador == colaborador_id,
            ColaboradorSkills.status.is_(True),
            ColaboradorSkills.deletado.is_(False),
        )
        .order_by(Skills.nome_skill)
    )
    return [ColaboradorSkillOut(**row) for row in db.execute(stmt).mappings()]


@router.get("", response_model=list[ColaboradorOut])
def listar_colaboradores(
    nome: Optional[str] = None,
    id_cargo: Optional[int] = None,
    id_senioridade: Optional[int] = None,
    apenas_ativos: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Colaboradores).where(Colaboradores.deletado.is_(False))
    if apenas_ativos:
        stmt = stmt.where(Colaboradores.status.is_(True))
    if nome:
        stmt = stmt.where(Colaboradores.nome_abreviado.ilike(f"%{nome}%"))
    if id_cargo:
        stmt = stmt.where(Colaboradores.id_cargo == id_cargo)
    if id_senioridade:
        stmt = stmt.where(Colaboradores.id_senioridade == id_senioridade)
    return db.scalars(stmt.order_by(Colaboradores.nome_abreviado).offset(skip).limit(limit)).all()


@router.get("/{colaborador_id}", response_model=ColaboradorDetalhe)
def obter_colaborador(colaborador_id: int, db: Session = Depends(get_db)):
    """Retorna o colaborador com nomes de cargo/senioridade/modalidade e suas skills."""
    colab = _buscar_ativo(db, colaborador_id)
    nomes = {
        d.id: d.valor_dominio
        for d in db.scalars(
            select(Dominios).where(Dominios.id.in_([colab.id_cargo, colab.id_senioridade, colab.id_modalidade]))
        )
    }
    detalhe = ColaboradorDetalhe.model_validate(colab)
    detalhe.cargo = nomes.get(colab.id_cargo)
    detalhe.senioridade = nomes.get(colab.id_senioridade)
    detalhe.modalidade = nomes.get(colab.id_modalidade)
    detalhe.skills = _skills_do_colaborador(db, colaborador_id)
    return detalhe


@router.post("", response_model=ColaboradorOut, status_code=status.HTTP_201_CREATED)
def criar_colaborador(dados: ColaboradorCreate, db: Session = Depends(get_db)):
    colab = Colaboradores(**dados.model_dump())
    db.add(colab)
    db.commit()
    db.refresh(colab)
    return colab


@router.patch("/{colaborador_id}", response_model=ColaboradorOut)
def atualizar_colaborador(colaborador_id: int, dados: ColaboradorUpdate, db: Session = Depends(get_db)):
    colab = _buscar_ativo(db, colaborador_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(colab, campo, valor)
    db.commit()
    db.refresh(colab)
    return colab


@router.delete("/{colaborador_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_colaborador(colaborador_id: int, db: Session = Depends(get_db)):
    """Exclusão lógica: marca deletado=true e status=false (o registro continua no banco)."""
    colab = _buscar_ativo(db, colaborador_id)
    colab.deletado = True
    colab.status = False
    db.commit()


# ---------------------------------------------------------------- Skills do colaborador
@router.get("/{colaborador_id}/skills", response_model=list[ColaboradorSkillOut])
def listar_skills(colaborador_id: int, db: Session = Depends(get_db)):
    _buscar_ativo(db, colaborador_id)
    return _skills_do_colaborador(db, colaborador_id)


@router.post("/{colaborador_id}/skills", response_model=ColaboradorSkillOut, status_code=status.HTTP_201_CREATED)
def adicionar_skill(colaborador_id: int, dados: ColaboradorSkillIn, db: Session = Depends(get_db)):
    """Adiciona uma skill ou atualiza o nível, se o colaborador já a possuir."""
    _buscar_ativo(db, colaborador_id)
    skill = db.get(Skills, dados.id_skill)
    if not skill or skill.deletado:
        raise HTTPException(404, "Skill não encontrada")

    id_nivel = db.scalar(
        select(Dominios.id).where(
            Dominios.tipo_dominio == "NIVEL_CONHECIMENTO",
            Dominios.valor_dominio == dados.nivel_conhecimento,
        )
    )
    if id_nivel is None:
        raise HTTPException(400, "Nível de conhecimento não cadastrado nos domínios")

    existente = db.scalar(
        select(ColaboradorSkills).where(
            ColaboradorSkills.id_colaborador == colaborador_id,
            ColaboradorSkills.id_skill == dados.id_skill,
            ColaboradorSkills.deletado.is_(False),
        )
    )
    if existente:
        existente.nivel_conhecimento = dados.nivel_conhecimento
        existente.id_nivel_conhecimento = id_nivel
        existente.status = True
        registro = existente
    else:
        registro = ColaboradorSkills(
            id_colaborador=colaborador_id,
            id_skill=dados.id_skill,
            nivel_conhecimento=dados.nivel_conhecimento,
            id_nivel_conhecimento=id_nivel,
        )
        db.add(registro)
    db.commit()
    db.refresh(registro)
    return ColaboradorSkillOut(
        id=registro.id, id_skill=registro.id_skill, nome_skill=skill.nome_skill,
        nivel_conhecimento=registro.nivel_conhecimento,
    )


@router.delete("/{colaborador_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_skill(colaborador_id: int, skill_id: int, db: Session = Depends(get_db)):
    registros = db.scalars(
        select(ColaboradorSkills).where(
            ColaboradorSkills.id_colaborador == colaborador_id,
            ColaboradorSkills.id_skill == skill_id,
            ColaboradorSkills.deletado.is_(False),
        )
    ).all()
    if not registros:
        raise HTTPException(404, "O colaborador não possui essa skill")
    for r in registros:
        r.deletado = True
        r.status = False
    db.commit()
