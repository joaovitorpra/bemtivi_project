"""Schemas (Pydantic) usados para validar entradas e formatar respostas da API."""
import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Mes = Literal["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
NivelConhecimento = Literal["BASICO", "INTERMEDIARIO", "AVANCADO"]


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- Domínios / Skills
class DominioOut(ORMBase):
    id: int
    tipo_dominio: str
    valor_dominio: str
    descricao: Optional[str] = None
    status: bool


class SkillOut(ORMBase):
    id: int
    nome_skill: str
    id_area_tecnologia: int


# ---------------------------------------------------------------- Colaboradores
class ColaboradorBase(BaseModel):
    nome_abreviado: str = Field(min_length=1, max_length=255)
    data_admissao: Optional[datetime.datetime] = None
    id_cargo: int
    id_senioridade: int
    id_step: int
    id_vinculo: int
    id_modalidade: int
    id_setor_empresa: Optional[int] = None
    id_contrato: Optional[int] = None


class ColaboradorCreate(ColaboradorBase):
    pass


class ColaboradorUpdate(BaseModel):
    nome_abreviado: Optional[str] = Field(default=None, min_length=1, max_length=255)
    data_admissao: Optional[datetime.datetime] = None
    id_cargo: Optional[int] = None
    id_senioridade: Optional[int] = None
    id_step: Optional[int] = None
    id_vinculo: Optional[int] = None
    id_modalidade: Optional[int] = None
    id_setor_empresa: Optional[int] = None
    id_contrato: Optional[int] = None
    status: Optional[bool] = None


class ColaboradorOut(ColaboradorBase, ORMBase):
    id: int
    status: bool


class ColaboradorSkillIn(BaseModel):
    id_skill: int
    nivel_conhecimento: NivelConhecimento


class ColaboradorSkillOut(BaseModel):
    id: int
    id_skill: int
    nome_skill: str
    nivel_conhecimento: str


class ColaboradorDetalhe(ColaboradorOut):
    cargo: Optional[str] = None
    senioridade: Optional[str] = None
    modalidade: Optional[str] = None
    skills: list[ColaboradorSkillOut] = []


# ---------------------------------------------------------------- Contratos
class ContratoOut(ORMBase):
    id: int
    nome_contrato: str
    data_inicio: datetime.date
    data_termino: datetime.date
    id_situacao: int
    id_centro_custo: int
    id_preposto: int
    status: bool


# ---------------------------------------------------------------- Demandas
class DemandaBase(BaseModel):
    nome_demanda: str = Field(min_length=1, max_length=100)
    id_gerente: int
    id_contrato: int
    id_tipo_servico: int
    id_metodologia: Optional[int] = None
    id_andamento_demanda: int
    id_grupo: Optional[int] = None
    dt_inicio_demanda: datetime.date
    dt_termino_demanda_prevista: datetime.date
    compartilha_profissionais: bool = False
    pertence_pmo: bool = False

    @model_validator(mode="after")
    def valida_datas(self):
        if self.dt_termino_demanda_prevista < self.dt_inicio_demanda:
            raise ValueError("dt_termino_demanda_prevista deve ser maior ou igual a dt_inicio_demanda")
        return self


class DemandaCreate(DemandaBase):
    skills: list[int] = Field(default_factory=list, description="IDs das skills exigidas")


class DemandaUpdate(BaseModel):
    nome_demanda: Optional[str] = Field(default=None, min_length=1, max_length=100)
    id_gerente: Optional[int] = None
    id_contrato: Optional[int] = None
    id_tipo_servico: Optional[int] = None
    id_metodologia: Optional[int] = None
    id_andamento_demanda: Optional[int] = None
    id_grupo: Optional[int] = None
    dt_inicio_demanda: Optional[datetime.date] = None
    dt_termino_demanda_prevista: Optional[datetime.date] = None
    compartilha_profissionais: Optional[bool] = None
    pertence_pmo: Optional[bool] = None
    status: Optional[bool] = None


class DemandaOut(DemandaBase, ORMBase):
    id: int
    status: bool


class DemandaDetalhe(DemandaOut):
    skills: list[SkillOut] = []


# ---------------------------------------------------------------- Alocações / Planejamentos
class AlocacaoCreate(BaseModel):
    id_colaborador: int
    id_demanda: int


class AlocacaoOut(ORMBase):
    id: int
    id_colaborador: int
    id_demanda: int
    status: bool


class PlanejamentoIn(BaseModel):
    mes: Mes
    ano: int = Field(ge=1, le=9999)
    porcentagem: int = Field(ge=0, le=100)


class PlanejamentoOut(ORMBase):
    id: int
    id_alocacao: int
    mes: str
    ano: int
    porcentagem: int


class AlocacaoDetalhe(AlocacaoOut):
    planejamentos: list[PlanejamentoOut] = []


# ---------------------------------------------------------------- Talentos
class TalentoOut(ORMBase):
    id: int
    nome_abreviado: str
    id_cargo: Optional[int] = None
    id_senioridade: Optional[int] = None
    id_modalidade: Optional[int] = None
    disponibilidade_informada_percentual: Optional[int] = None
    status: bool


class TalentoDetalhe(TalentoOut):
    skills: list[SkillOut] = []


# ---------------------------------------------------------------- Busca inteligente
class ProfissionalBusca(BaseModel):
    id_colaborador: int
    nome_ficticio: str
    id_cargo: int
    id_senioridade: int
    total_alocado: int
    disponibilidade: int


class RankingSkill(BaseModel):
    id_colaborador: int
    nome_ficticio: str
    senioridade: Optional[str] = None
    skills_atendidas: int
    skills_pedidas: int
    score_percentual: Decimal
    total_alocado: int
    disponibilidade: int


class RankingTalento(BaseModel):
    id_talento: int
    nome_talento: str
    skills_atendidas: int
    skills_pedidas: int
    score_percentual: Decimal


class DisponibilidadeMensal(BaseModel):
    id_colaborador: int
    nome_abreviado: str
    total_alocado: int
    disponibilidade: int


class DisponibilidadePeriodo(BaseModel):
    id_colaborador: int
    meses: int
    disponibilidade_media: Decimal
    disponibilidade_minima: int
    disponibilidade_maxima: int
    meses_sem_alocacao: int


class SugestaoDemanda(BaseModel):
    demanda: str
    skills_exigidas: list[str]
    colaboradores: list[RankingSkill]
    talentos_externos: list[RankingTalento]
