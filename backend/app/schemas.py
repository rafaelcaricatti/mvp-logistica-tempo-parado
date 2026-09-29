"""Schemas Pydantic — contrato de entrada/saída da API.

Espelham o modelo de dados da seção 8 da Especificação de Requisitos.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Perfis de acesso (RNF04)
# ---------------------------------------------------------------------------
class Perfil(StrEnum):
    MOTORISTA = "motorista"
    GERENTE = "gerente"
    ADMINISTRADOR = "administrador"


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em: datetime
    usuario: "UsuarioOut"


class UsuarioBase(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str
    perfil: Perfil
    motorista_id: str | None = Field(
        default=None, description="Vínculo com o cadastro de motorista (perfil motorista)"
    )
    gerente_id: str | None = Field(
        default=None, description="Vínculo com o cadastro de gerente (perfil gerente)"
    )
    ativo: bool = True


class UsuarioCreate(UsuarioBase):
    senha: str = Field(min_length=4, max_length=128)


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    perfil: Perfil | None = None
    senha: str | None = Field(default=None, min_length=4, max_length=128)
    motorista_id: str | None = None
    gerente_id: str | None = None
    ativo: bool | None = None


class UsuarioOut(UsuarioBase):
    id: str


# ---------------------------------------------------------------------------
# RF01 — Motorista / Motoboy
# ---------------------------------------------------------------------------
class MotoristaBase(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    telefone: str = Field(min_length=8, max_length=25)
    documento: str = Field(min_length=5, max_length=30, description="CPF ou CNH")
    veiculo: str = Field(min_length=2, max_length=80)
    rendimento_km_l: float = Field(gt=0, description="Rendimento do veículo em km/litro")
    ativo: bool = True


class MotoristaCreate(MotoristaBase):
    pass


class MotoristaUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    documento: str | None = None
    veiculo: str | None = None
    rendimento_km_l: float | None = Field(default=None, gt=0)
    ativo: bool | None = None


class MotoristaOut(MotoristaBase):
    id: str


# ---------------------------------------------------------------------------
# RF02 — Gerente / Coordenador / Dono da transportadora
# ---------------------------------------------------------------------------
class GerenteBase(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    telefone: str = Field(min_length=8, max_length=25)
    email: EmailStr
    equipe: list[str] = Field(
        default_factory=list, description="IDs dos motoristas sob responsabilidade"
    )
    ativo: bool = True


class GerenteCreate(GerenteBase):
    pass


class GerenteUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    email: EmailStr | None = None
    equipe: list[str] | None = None
    ativo: bool | None = None


class GerenteOut(GerenteBase):
    id: str


# ---------------------------------------------------------------------------
# RF03 — Ponto (cadastro de endereços reutilizáveis)
# ---------------------------------------------------------------------------
class PontoBase(BaseModel):
    apelido: str | None = Field(default=None, max_length=80)
    endereco: str = Field(min_length=3, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PontoCreate(PontoBase):
    pass


class PontoUpdate(BaseModel):
    apelido: str | None = None
    endereco: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PontoOut(PontoBase):
    id: str


# ---------------------------------------------------------------------------
# RF04 / RF05 / RF06 — Roteiro e suas paradas
# ---------------------------------------------------------------------------
class StatusParada(StrEnum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"


class StatusRoteiro(StrEnum):
    PLANEJADO = "planejado"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"


class ParadaCreate(BaseModel):
    """Ponto do roteiro informado no planejamento (RF04)."""

    ponto_id: str | None = Field(default=None, description="ID de um ponto já cadastrado")
    endereco: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    observacao: str | None = None

    @field_validator("endereco")
    @classmethod
    def _limpa(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ParadaOut(BaseModel):
    ordem: int
    ponto_id: str | None = None
    endereco: str
    latitude: float | None = None
    longitude: float | None = None
    chegada: datetime | None = None
    saida: datetime | None = None
    tempo_parado_min: float | None = None
    ponto_de_partida: bool = False
    status: StatusParada = StatusParada.PENDENTE
    observacao: str | None = None


class RoteiroCreate(BaseModel):
    data: date
    motorista_id: str
    distancia_total_km: float = Field(default=0.0, ge=0)
    pontos: list[ParadaCreate] = Field(min_length=2, description="RN06 — ordem sequencial")
    observacao: str | None = None


class RoteiroUpdate(BaseModel):
    data: date | None = None
    motorista_id: str | None = None
    distancia_total_km: float | None = Field(default=None, ge=0)
    observacao: str | None = None


class CustoRoteiro(BaseModel):
    litros_estimados: float
    custo_combustivel: float
    custo_por_km_total: float
    custo_total_estimado: float
    valor_combustivel: float
    rendimento_km_l: float
    custo_por_km: float


class RoteiroOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    data: date
    motorista_id: str
    motorista_nome: str | None = None
    distancia_total_km: float
    pontos: list[ParadaOut]
    tempo_total_parado_min: float
    percentual_jornada: float = Field(
        description="RN04 — tempo parado como fração da jornada padrão (8 h = 1.0)"
    )
    custo_estimado: float
    custo_detalhado: CustoRoteiro | None = None
    status: StatusRoteiro
    observacao: str | None = None
    criado_em: datetime | None = None
    atualizado_em: datetime | None = None


class RegistroPonto(BaseModel):
    """Registro manual de chegada/saída (RF05). Sem valor = usa o horário atual."""

    horario: datetime | None = None


# ---------------------------------------------------------------------------
# RF09 / RF10 — Parâmetros
# ---------------------------------------------------------------------------
class ParametrosBase(BaseModel):
    valor_combustivel: float = Field(gt=0, description="R$ por litro")
    custo_por_km: float = Field(ge=0, description="Custo operacional por km rodado (R$)")
    rendimento_km_l_padrao: float = Field(
        gt=0, description="Rendimento usado quando o veículo não informa o próprio"
    )
    jornada_horas: float = Field(gt=0, le=24, description="RN04 — jornada padrão (8 h/dia)")
    # RF10 — regras de cálculo do tempo parado
    contar_ponto_partida: bool = Field(
        default=False, description="RN01 — por padrão o ponto de partida não conta tempo"
    )
    tolerancia_minutos: float = Field(
        default=0.0, ge=0, description="Paradas abaixo da tolerância são desprezadas"
    )
    arredondamento_minutos: int = Field(
        default=1, ge=0, le=60, description="Granularidade do arredondamento (0 = sem arredondar)"
    )


class ParametrosUpdate(BaseModel):
    valor_combustivel: float | None = Field(default=None, gt=0)
    custo_por_km: float | None = Field(default=None, ge=0)
    rendimento_km_l_padrao: float | None = Field(default=None, gt=0)
    jornada_horas: float | None = Field(default=None, gt=0, le=24)
    contar_ponto_partida: bool | None = None
    tolerancia_minutos: float | None = Field(default=None, ge=0)
    arredondamento_minutos: int | None = Field(default=None, ge=0, le=60)


class ParametrosOut(ParametrosBase):
    atualizado_em: datetime | None = None
    atualizado_por: str | None = None


# ---------------------------------------------------------------------------
# RF07 — Histórico
# ---------------------------------------------------------------------------
class ItemHistorico(BaseModel):
    roteiro_id: str
    data: date
    motorista_id: str
    motorista_nome: str | None = None
    ordem: int
    endereco: str
    latitude: float | None = None
    longitude: float | None = None
    chegada: datetime | None = None
    saida: datetime | None = None
    tempo_parado_min: float
    ponto_de_partida: bool


class HistoricoOut(BaseModel):
    inicio: date
    fim: date
    total_registros: int
    tempo_total_parado_min: float
    itens: list[ItemHistorico]


# ---------------------------------------------------------------------------
# RF08 — Dashboard
# ---------------------------------------------------------------------------
class Agrupamento(StrEnum):
    DIA = "dia"
    MES = "mes"
    PERIODO = "periodo"


class SerieItem(BaseModel):
    rotulo: str
    tempo_parado_min: float
    distancia_km: float
    roteiros: int
    paradas: int
    custo_estimado: float


class IndicadoresDashboard(BaseModel):
    tempo_total_parado_min: float
    tempo_medio_por_parada_min: float
    distancia_total_km: float
    total_roteiros: int
    total_paradas: int
    custo_total_estimado: float
    jornada_horas: float
    jornadas_equivalentes: float = Field(description="RN04 — tempo parado / jornada padrão")
    percentual_jornada: float


class RankingItem(BaseModel):
    chave: str
    rotulo: str
    tempo_parado_min: float
    ocorrencias: int


class DashboardOut(BaseModel):
    agrupamento: Agrupamento
    inicio: date
    fim: date
    motorista_id: str | None = None
    serie: list[SerieItem]
    indicadores: IndicadoresDashboard
    ranking_enderecos: list[RankingItem]
    ranking_motoristas: list[RankingItem]


# ---------------------------------------------------------------------------
# RNF05 — Auditoria
# ---------------------------------------------------------------------------
class AuditoriaOut(BaseModel):
    id: str
    ocorrido_em: datetime
    usuario_id: str | None = None
    usuario_email: str | None = None
    perfil: str | None = None
    acao: str
    entidade: str
    entidade_id: str | None = None
    detalhes: dict | None = None


class MensagemOut(BaseModel):
    detalhe: str
