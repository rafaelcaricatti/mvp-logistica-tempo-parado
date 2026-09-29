"""RF07/RF08 — Histórico e dashboard."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.security import qualquer_perfil
from app.schemas import Agrupamento, DashboardOut, HistoricoOut, UsuarioOut
from app.services import dashboard as svc

router = APIRouter(tags=["RF07-RF08 · Histórico e Dashboard"])


@router.get(
    "/historico",
    response_model=HistoricoOut,
    summary="RF07 — pontos e tempos parados por período, com endereços",
)
def historico(
    inicio: date | None = Query(default=None),
    fim: date | None = Query(default=None),
    motorista_id: str | None = None,
    somente_concluidos: bool = False,
    usuario: UsuarioOut = Depends(qualquer_perfil()),
) -> HistoricoOut:
    return svc.historico(inicio, fim, motorista_id, somente_concluidos, usuario=usuario)


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    summary="RF08 — série de tempo parado por dia, por mês ou por período",
)
def dashboard(
    agrupamento: Agrupamento = Agrupamento.DIA,
    inicio: date | None = Query(default=None),
    fim: date | None = Query(default=None),
    motorista_id: str | None = None,
    usuario: UsuarioOut = Depends(qualquer_perfil()),
) -> DashboardOut:
    return svc.dashboard(agrupamento, inicio, fim, motorista_id, usuario=usuario)
