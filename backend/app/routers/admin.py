"""Operações administrativas (carga inicial / demonstração)."""

from fastapi import APIRouter, Depends

from app.core.security import apenas_admin
from app.schemas import UsuarioOut
from app.services import seed as svc

router = APIRouter(prefix="/admin", tags=["Administração"])


@router.post("/seed", summary="Popula a base com dados de demonstração")
def seed(
    com_demo: bool = True,
    dias_historico: int = 120,
    _: UsuarioOut = Depends(apenas_admin()),
) -> dict:
    return svc.executar(com_demo=com_demo, dias_historico=dias_historico)
