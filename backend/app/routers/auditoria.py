"""RNF05 — Consulta da trilha de auditoria."""

from fastapi import APIRouter, Depends, Query

from app.core.security import apenas_gestao
from app.schemas import AuditoriaOut, UsuarioOut
from app.services import auditoria as svc

router = APIRouter(prefix="/auditoria", tags=["RNF05 · Auditoria"])


@router.get("", response_model=list[AuditoriaOut], summary="Lista eventos de auditoria")
def listar(
    entidade: str | None = None,
    entidade_id: str | None = None,
    limite: int = Query(default=200, ge=1, le=1000),
    _: UsuarioOut = Depends(apenas_gestao()),
) -> list[AuditoriaOut]:
    return svc.listar(entidade, entidade_id, limite)
