"""RF09/RF10 — Parâmetros de custo e de cálculo do tempo parado."""

from fastapi import APIRouter, Depends

from app.core.security import apenas_gestao, qualquer_perfil
from app.schemas import ParametrosOut, ParametrosUpdate, UsuarioOut
from app.services import parametros as svc

router = APIRouter(prefix="/parametros", tags=["RF09-RF10 · Parâmetros"])


@router.get("", response_model=ParametrosOut, summary="Lê os parâmetros vigentes")
def obter(_: UsuarioOut = Depends(qualquer_perfil())) -> ParametrosOut:
    return svc.obter()


@router.put("", response_model=ParametrosOut, summary="Altera custos e jornada padrão")
def atualizar(
    payload: ParametrosUpdate, usuario: UsuarioOut = Depends(apenas_gestao())
) -> ParametrosOut:
    return svc.atualizar(payload, usuario)
