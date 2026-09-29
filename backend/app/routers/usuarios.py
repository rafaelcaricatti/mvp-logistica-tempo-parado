"""Gestão de usuários e perfis de acesso (RNF04)."""

from fastapi import APIRouter, Depends, status

from app.core.security import apenas_admin
from app.schemas import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services import usuarios as svc

router = APIRouter(prefix="/usuarios", tags=["RNF04 · Usuários e perfis"])


@router.get("", response_model=list[UsuarioOut], summary="Lista usuários")
def listar(_: UsuarioOut = Depends(apenas_admin())) -> list[UsuarioOut]:
    return svc.listar()


@router.post(
    "", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED, summary="Cria usuário"
)
def criar(payload: UsuarioCreate, usuario: UsuarioOut = Depends(apenas_admin())) -> UsuarioOut:
    return svc.criar(payload, usuario)


@router.put("/{usuario_id}", response_model=UsuarioOut, summary="Atualiza usuário")
def atualizar(
    usuario_id: str, payload: UsuarioUpdate, usuario: UsuarioOut = Depends(apenas_admin())
) -> UsuarioOut:
    return svc.atualizar(usuario_id, payload, usuario)


@router.delete(
    "/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove usuário"
)
def remover(usuario_id: str, usuario: UsuarioOut = Depends(apenas_admin())) -> None:
    svc.remover(usuario_id, usuario)
