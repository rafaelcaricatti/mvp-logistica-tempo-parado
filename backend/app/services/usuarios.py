"""Usuários e autenticação (RNF04)."""

from __future__ import annotations

from fastapi import HTTPException, status

from app import repositories
from app.core.security import criar_token, gerar_hash_senha, verificar_senha
from app.schemas import Perfil, UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services import auditoria


def _sem_senha(registro: dict) -> UsuarioOut:
    limpo = {k: v for k, v in registro.items() if k != "senha_hash"}
    return UsuarioOut(**limpo)


def por_email(email: str) -> dict | None:
    return repositories.usuarios().primeiro([("email", "==", email.strip().lower())])


def criar(payload: UsuarioCreate, usuario: UsuarioOut | None = None) -> UsuarioOut:
    email = payload.email.strip().lower()
    if por_email(email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"O e-mail '{email}' já está em uso."
        )
    dados = payload.model_dump(exclude={"senha"})
    dados["email"] = email
    dados["perfil"] = str(payload.perfil)
    dados["senha_hash"] = gerar_hash_senha(payload.senha)
    registro = repositories.usuarios().criar(dados)
    auditoria.registrar("criar", "usuario", registro["id"], usuario, {"email": email})
    return _sem_senha(registro)


def listar() -> list[UsuarioOut]:
    return [_sem_senha(r) for r in repositories.usuarios().listar(ordenar_por="nome")]


def obter(usuario_id: str) -> UsuarioOut:
    registro = repositories.usuarios().obter(usuario_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return _sem_senha(registro)


def atualizar(
    usuario_id: str, payload: UsuarioUpdate, usuario: UsuarioOut | None = None
) -> UsuarioOut:
    if repositories.usuarios().obter(usuario_id) is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    mudancas = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "senha" in mudancas:
        mudancas["senha_hash"] = gerar_hash_senha(mudancas.pop("senha"))
    if "email" in mudancas:
        mudancas["email"] = mudancas["email"].strip().lower()
    if "perfil" in mudancas:
        mudancas["perfil"] = str(mudancas["perfil"])
    registro = repositories.usuarios().atualizar(usuario_id, mudancas)
    auditoria.registrar(
        "atualizar", "usuario", usuario_id, usuario, {"campos": sorted(mudancas)}
    )
    return _sem_senha(registro)


def remover(usuario_id: str, usuario: UsuarioOut | None = None) -> None:
    if not repositories.usuarios().remover(usuario_id):
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    auditoria.registrar("remover", "usuario", usuario_id, usuario)


def autenticar(email: str, senha: str):
    registro = por_email(email)
    if registro is None or not verificar_senha(senha, registro.get("senha_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos."
        )
    if not registro.get("ativo", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")
    token, expira = criar_token(registro)
    return token, expira, _sem_senha(registro)


def garantir_admin(email: str, senha: str) -> None:
    """Cria o administrador inicial se ainda não existir."""
    if por_email(email):
        return
    criar(
        UsuarioCreate(
            nome="Administrador", email=email, senha=senha, perfil=Perfil.ADMINISTRADOR
        )
    )
