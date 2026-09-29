"""Autenticação — RNF04."""

from fastapi import APIRouter, Depends

from app.core.security import usuario_atual
from app.schemas import LoginRequest, TokenResponse, UsuarioOut
from app.services import usuarios as svc

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse, summary="Autentica e devolve o token")
def login(payload: LoginRequest) -> TokenResponse:
    token, expira, usuario = svc.autenticar(payload.email, payload.senha)
    return TokenResponse(access_token=token, expira_em=expira, usuario=usuario)


@router.get("/me", response_model=UsuarioOut, summary="Dados do usuário autenticado")
def me(usuario: UsuarioOut = Depends(usuario_atual)) -> UsuarioOut:
    return usuario
