from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint, String, Table, Text, UniqueConstraint, text
from typing import Optional
import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Models gerados a partir do schema "InHire" importado no Supabase.
# Eles refletem as tabelas existentes; nao altere colunas aqui sem alterar o banco.


class Colaboradores(Base):
    __tablename__ = 'colaboradores'
    __table_args__ = (
        CheckConstraint("btrim(nome_abreviado::text) <> ''::text", name='colaboradores_nome_abreviado_check'),
        ForeignKeyConstraint(['id_cargo'], ['InHire.dominios.id'], ondelete='RESTRICT', name='colaboradores_id_cargo_fkey'),
        ForeignKeyConstraint(['id_contrato'], ['InHire.contratos.id'], deferrable=True, initially='DEFERRED', name='colaboradores_id_contrato_fkey'),
        ForeignKeyConstraint(['id_modalidade'], ['InHire.dominios.id'], ondelete='RESTRICT', name='colaboradores_id_modalidade_fkey'),
        ForeignKeyConstraint(['id_senioridade'], ['InHire.dominios.id'], ondelete='RESTRICT', name='colaboradores_id_senioridade_fkey'),
        ForeignKeyConstraint(['id_setor_empresa'], ['InHire.dominios.id'], ondelete='RESTRICT', name='colaboradores_id_setor_empresa_fkey'),
        ForeignKeyConstraint(['id_step'], ['InHire.dominios.id'], ondelete='RESTRICT', name='colaboradores_id_step_fkey'),
        ForeignKeyConstraint(['id_vinculo'], ['InHire.dominios.id'], ondelete='RESTRICT', name='colaboradores_id_vinculo_fkey'),
        PrimaryKeyConstraint('id', name='colaboradores_pkey'),
        Index('ix_colaboradores_cargo', 'id_cargo'),
        Index('ix_colaboradores_contrato', 'id_contrato'),
        Index('ix_colaboradores_modalidade', 'id_modalidade'),
        Index('ix_colaboradores_senioridade', 'id_senioridade'),
        Index('ix_colaboradores_setor', 'id_setor_empresa'),
        Index('ix_colaboradores_step', 'id_step'),
        Index('ix_colaboradores_vinculo', 'id_vinculo'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome_abreviado: Mapped[str] = mapped_column(String(255), nullable=False)
    id_cargo: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_senioridade: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_step: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_vinculo: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_modalidade: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    data_admissao: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    id_setor_empresa: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_contrato: Mapped[Optional[int]] = mapped_column(BigInteger)



class Contratos(Base):
    __tablename__ = 'contratos'
    __table_args__ = (
        CheckConstraint("btrim(nome_contrato::text) <> ''::text", name='contratos_nome_contrato_check'),
        CheckConstraint('data_termino >= data_inicio', name='contratos_check'),
        ForeignKeyConstraint(['id_centro_custo'], ['InHire.dominios.id'], ondelete='RESTRICT', name='contratos_id_centro_custo_fkey'),
        ForeignKeyConstraint(['id_preposto'], ['InHire.colaboradores.id'], deferrable=True, initially='DEFERRED', name='fk_contratos_preposto'),
        ForeignKeyConstraint(['id_situacao'], ['InHire.dominios.id'], ondelete='RESTRICT', name='contratos_id_situacao_fkey'),
        PrimaryKeyConstraint('id', name='contratos_pkey'),
        Index('ix_contratos_centro_custo', 'id_centro_custo'),
        Index('ix_contratos_preposto', 'id_preposto'),
        Index('ix_contratos_situacao', 'id_situacao'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome_contrato: Mapped[str] = mapped_column(String(100), nullable=False)
    data_inicio: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    data_termino: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    id_situacao: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_centro_custo: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_preposto: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))



class Dominios(Base):
    __tablename__ = 'dominios'
    __table_args__ = (
        CheckConstraint("btrim(tipo_dominio::text) <> ''::text", name='dominios_tipo_dominio_check'),
        CheckConstraint("btrim(valor_dominio::text) <> ''::text", name='dominios_valor_dominio_check'),
        PrimaryKeyConstraint('id', name='dominios_pkey'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo_dominio: Mapped[str] = mapped_column(String(100), nullable=False)
    valor_dominio: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    descricao: Mapped[Optional[str]] = mapped_column(String(255))



t_vw_inconsistencias_dominios = Table(
    'vw_inconsistencias_dominios', Base.metadata,
    Column('tabela', Text),
    Column('id_registro', BigInteger),
    Column('campo', Text),
    Column('id_dominio', BigInteger),
    Column('tipo_esperado', Text),
    Column('tipo_encontrado', String(100)),
    schema='InHire'
)


class Demandas(Base):
    __tablename__ = 'demandas'
    __table_args__ = (
        CheckConstraint("btrim(nome_demanda::text) <> ''::text", name='demandas_nome_demanda_check'),
        CheckConstraint('dt_termino_demanda_prevista >= dt_inicio_demanda', name='demandas_check'),
        ForeignKeyConstraint(['id_andamento_demanda'], ['InHire.dominios.id'], ondelete='RESTRICT', name='demandas_id_andamento_demanda_fkey'),
        ForeignKeyConstraint(['id_contrato'], ['InHire.contratos.id'], ondelete='RESTRICT', name='demandas_id_contrato_fkey'),
        ForeignKeyConstraint(['id_gerente'], ['InHire.colaboradores.id'], ondelete='RESTRICT', name='demandas_id_gerente_fkey'),
        ForeignKeyConstraint(['id_grupo'], ['InHire.dominios.id'], ondelete='RESTRICT', name='demandas_id_grupo_fkey'),
        ForeignKeyConstraint(['id_metodologia'], ['InHire.dominios.id'], ondelete='RESTRICT', name='demandas_id_metodologia_fkey'),
        ForeignKeyConstraint(['id_tipo_servico'], ['InHire.dominios.id'], ondelete='RESTRICT', name='demandas_id_tipo_servico_fkey'),
        PrimaryKeyConstraint('id', name='demandas_pkey'),
        Index('ix_demandas_andamento', 'id_andamento_demanda'),
        Index('ix_demandas_contrato', 'id_contrato'),
        Index('ix_demandas_gerente', 'id_gerente'),
        Index('ix_demandas_grupo', 'id_grupo'),
        Index('ix_demandas_metodologia', 'id_metodologia'),
        Index('ix_demandas_tipo_servico', 'id_tipo_servico'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome_demanda: Mapped[str] = mapped_column(String(100), nullable=False)
    id_gerente: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_contrato: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_tipo_servico: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_andamento_demanda: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dt_inicio_demanda: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    dt_termino_demanda_prevista: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    compartilha_profissionais: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    pertence_pmo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    id_metodologia: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_grupo: Mapped[Optional[int]] = mapped_column(BigInteger)



class Skills(Base):
    __tablename__ = 'skills'
    __table_args__ = (
        CheckConstraint("btrim(nome_skill::text) <> ''::text", name='skills_nome_skill_check'),
        ForeignKeyConstraint(['id_area_tecnologia'], ['InHire.dominios.id'], ondelete='RESTRICT', name='skills_id_area_tecnologia_fkey'),
        PrimaryKeyConstraint('id', name='skills_pkey'),
        Index('uq_skills_area_nome', 'id_area_tecnologia', text('lower(btrim(nome_skill::text))'), unique=True),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome_skill: Mapped[str] = mapped_column(String(100), nullable=False)
    id_area_tecnologia: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))



class Talentos(Base):
    __tablename__ = 'talentos'
    __table_args__ = (
        CheckConstraint("btrim(nome_abreviado::text) <> ''::text", name='talentos_nome_abreviado_check'),
        CheckConstraint('disponibilidade_informada_percentual >= 0 AND disponibilidade_informada_percentual <= 100', name='talentos_disponibilidade_informada_percentual_check'),
        ForeignKeyConstraint(['id_cargo'], ['InHire.dominios.id'], ondelete='RESTRICT', name='talentos_id_cargo_fkey'),
        ForeignKeyConstraint(['id_modalidade'], ['InHire.dominios.id'], ondelete='RESTRICT', name='talentos_id_modalidade_fkey'),
        ForeignKeyConstraint(['id_senioridade'], ['InHire.dominios.id'], ondelete='RESTRICT', name='talentos_id_senioridade_fkey'),
        PrimaryKeyConstraint('id', name='talentos_pkey'),
        Index('ix_talentos_cargo', 'id_cargo'),
        Index('ix_talentos_modalidade', 'id_modalidade'),
        Index('ix_talentos_senioridade', 'id_senioridade'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome_abreviado: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    id_cargo: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_senioridade: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_modalidade: Mapped[Optional[int]] = mapped_column(BigInteger)
    disponibilidade_informada_percentual: Mapped[Optional[int]] = mapped_column(Integer)



class Alocacoes(Base):
    __tablename__ = 'alocacoes'
    __table_args__ = (
        ForeignKeyConstraint(['id_colaborador'], ['InHire.colaboradores.id'], ondelete='RESTRICT', name='alocacoes_id_colaborador_fkey'),
        ForeignKeyConstraint(['id_demanda'], ['InHire.demandas.id'], ondelete='RESTRICT', name='alocacoes_id_demanda_fkey'),
        PrimaryKeyConstraint('id', name='alocacoes_pkey'),
        Index('ix_alocacoes_ativas', 'id_colaborador', 'id', postgresql_where='((status IS TRUE) AND (deletado IS FALSE))'),
        Index('ix_alocacoes_colaborador_demanda', 'id_colaborador', 'id_demanda'),
        Index('ix_alocacoes_demanda', 'id_demanda'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_colaborador: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_demanda: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))



class ColaboradorSkills(Base):
    __tablename__ = 'colaborador_skills'
    __table_args__ = (
        CheckConstraint("nivel_conhecimento::text = ANY (ARRAY['BASICO'::character varying::text, 'INTERMEDIARIO'::character varying::text, 'AVANCADO'::character varying::text])", name='colaborador_skills_nivel_conhecimento_check'),
        ForeignKeyConstraint(['id_colaborador'], ['InHire.colaboradores.id'], ondelete='RESTRICT', name='colaborador_skills_id_colaborador_fkey'),
        ForeignKeyConstraint(['id_nivel_conhecimento'], ['InHire.dominios.id'], ondelete='RESTRICT', name='colaborador_skills_id_nivel_conhecimento_fkey'),
        ForeignKeyConstraint(['id_skill'], ['InHire.skills.id'], ondelete='RESTRICT', name='colaborador_skills_id_skill_fkey'),
        PrimaryKeyConstraint('id', name='colaborador_skills_pkey'),
        Index('ix_cs_colaborador_skill', 'id_colaborador', 'id_skill'),
        Index('ix_cs_nivel', 'id_nivel_conhecimento'),
        Index('ix_cs_skill', 'id_skill'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_colaborador: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_skill: Mapped[int] = mapped_column(BigInteger, nullable=False)
    nivel_conhecimento: Mapped[str] = mapped_column(String(20), nullable=False)
    id_nivel_conhecimento: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))



class DemandaSkills(Base):
    __tablename__ = 'demanda_skills'
    __table_args__ = (
        ForeignKeyConstraint(['id_demanda'], ['InHire.demandas.id'], ondelete='RESTRICT', name='demanda_skills_id_demanda_fkey'),
        ForeignKeyConstraint(['id_skill'], ['InHire.skills.id'], ondelete='RESTRICT', name='demanda_skills_id_skill_fkey'),
        PrimaryKeyConstraint('id', name='demanda_skills_pkey'),
        Index('ix_ds_demanda_skill', 'id_demanda', 'id_skill'),
        Index('ix_ds_skill', 'id_skill'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_demanda: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_skill: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))



class TalentoSkills(Base):
    __tablename__ = 'talento_skills'
    __table_args__ = (
        ForeignKeyConstraint(['id_nivel_conhecimento'], ['InHire.dominios.id'], ondelete='RESTRICT', name='talento_skills_id_nivel_conhecimento_fkey'),
        ForeignKeyConstraint(['id_skill'], ['InHire.skills.id'], ondelete='RESTRICT', name='talento_skills_id_skill_fkey'),
        ForeignKeyConstraint(['id_talento'], ['InHire.talentos.id'], ondelete='CASCADE', name='talento_skills_id_talento_fkey'),
        PrimaryKeyConstraint('id', name='talento_skills_pkey'),
        UniqueConstraint('id_talento', 'id_skill', name='talento_skills_id_talento_id_skill_key'),
        Index('ix_ts_nivel', 'id_nivel_conhecimento'),
        Index('ix_ts_skill', 'id_skill'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_talento: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_skill: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_nivel_conhecimento: Mapped[int] = mapped_column(BigInteger, nullable=False)



class Planejamentos(Base):
    __tablename__ = 'planejamentos'
    __table_args__ = (
        CheckConstraint('ano >= 1 AND ano <= 9999', name='planejamentos_ano_check'),
        CheckConstraint("mes::text = ANY (ARRAY['Jan'::character varying::text, 'Fev'::character varying::text, 'Mar'::character varying::text, 'Abr'::character varying::text, 'Mai'::character varying::text, 'Jun'::character varying::text, 'Jul'::character varying::text, 'Ago'::character varying::text, 'Set'::character varying::text, 'Out'::character varying::text, 'Nov'::character varying::text, 'Dez'::character varying::text])", name='planejamentos_mes_check'),
        CheckConstraint('porcentagem >= 0 AND porcentagem <= 100', name='planejamentos_porcentagem_check'),
        ForeignKeyConstraint(['id_alocacao'], ['InHire.alocacoes.id'], ondelete='RESTRICT', name='planejamentos_id_alocacao_fkey'),
        PrimaryKeyConstraint('id', name='planejamentos_pkey'),
        UniqueConstraint('id_alocacao', 'mes', 'ano', name='planejamentos_id_alocacao_mes_ano_key'),
        Index('ix_planejamentos_competencia', 'ano', 'mes', 'id_alocacao'),
        {'schema': 'InHire'}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_alocacao: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mes: Mapped[str] = mapped_column(String(3), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    porcentagem: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    deletado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))


