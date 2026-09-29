"""RF04/RF05/RF06/RF11 — Roteiros, coleta de horários e cálculos."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.core.security import apenas_gestao, qualquer_perfil
from app.schemas import (
    ParadaCreate,
    RegistroPonto,
    RoteiroCreate,
    RoteiroOut,
    RoteiroUpdate,
    UsuarioOut,
)
from app.services import roteiros as svc

router = APIRouter(prefix="/roteiros", tags=["RF04-RF06 · Roteiros"])


@router.get("", response_model=list[RoteiroOut], summary="Lista roteiros do período")
def listar(
    inicio: date | None = Query(default=None, description="Data inicial (YYYY-MM-DD)"),
    fim: date | None = Query(default=None, description="Data final (YYYY-MM-DD)"),
    motorista_id: str | None = None,
    usuario: UsuarioOut = Depends(qualquer_perfil()),
) -> list[RoteiroOut]:
    return svc.listar(inicio, fim, motorista_id, usuario=usuario)


@router.get("/{roteiro_id}", response_model=RoteiroOut, summary="Detalha um roteiro")
def obter(roteiro_id: str, usuario: UsuarioOut = Depends(qualquer_perfil())) -> RoteiroOut:
    registro = svc.obter_raw(roteiro_id)
    svc.checar_acesso(registro, usuario)
    return svc.obter(roteiro_id)


@router.post(
    "",
    response_model=RoteiroOut,
    status_code=status.HTTP_201_CREATED,
    summary="RF04 — monta o roteiro diário",
)
def criar(payload: RoteiroCreate, usuario: UsuarioOut = Depends(apenas_gestao())) -> RoteiroOut:
    return svc.criar(payload, usuario)


@router.put("/{roteiro_id}", response_model=RoteiroOut, summary="Atualiza dados do roteiro")
def atualizar(
    roteiro_id: str, payload: RoteiroUpdate, usuario: UsuarioOut = Depends(apenas_gestao())
) -> RoteiroOut:
    return svc.atualizar(roteiro_id, payload, usuario)


@router.delete(
    "/{roteiro_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove um roteiro"
)
def remover(roteiro_id: str, usuario: UsuarioOut = Depends(apenas_gestao())) -> None:
    svc.remover(roteiro_id, usuario)


@router.post(
    "/{roteiro_id}/pontos",
    response_model=RoteiroOut,
    summary="Acrescenta um ponto ao final do roteiro",
)
def adicionar_parada(
    roteiro_id: str, payload: ParadaCreate, usuario: UsuarioOut = Depends(apenas_gestao())
) -> RoteiroOut:
    return svc.adicionar_parada(roteiro_id, payload, usuario)


@router.post(
    "/{roteiro_id}/pontos/{ordem}/chegada",
    response_model=RoteiroOut,
    summary="RF05 — registra a chegada no ponto",
)
def registrar_chegada(
    roteiro_id: str,
    ordem: int,
    payload: RegistroPonto | None = None,
    usuario: UsuarioOut = Depends(qualquer_perfil()),
) -> RoteiroOut:
    horario = payload.horario if payload else None
    return svc.registrar_chegada(roteiro_id, ordem, horario, usuario)


@router.post(
    "/{roteiro_id}/pontos/{ordem}/saida",
    response_model=RoteiroOut,
    summary="RF05 — registra a saída do ponto",
)
def registrar_saida(
    roteiro_id: str,
    ordem: int,
    payload: RegistroPonto | None = None,
    usuario: UsuarioOut = Depends(qualquer_perfil()),
) -> RoteiroOut:
    horario = payload.horario if payload else None
    return svc.registrar_saida(roteiro_id, ordem, horario, usuario)
