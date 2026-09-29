"""Autenticação e controle de acesso por perfil (RNF04).

Token próprio assinado com HMAC-SHA256 (mesmo formato de um JWT compacto),
implementado só com a biblioteca padrão para não acrescentar dependências.
Senhas são guardadas como PBKDF2-HMAC-SHA256 + salt, nunca em texto puro
(RNF06 / LGPD).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.schemas import Perfil, UsuarioOut

_ITERACOES = 120_000
_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Senhas
# ---------------------------------------------------------------------------
def gerar_hash_senha(senha: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), _ITERACOES)
    return f"pbkdf2_sha256${_ITERACOES}${salt}${digest.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        algoritmo, iteracoes, salt, esperado = hash_armazenado.split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), int(iteracoes))
    return hmac.compare_digest(digest.hex(), esperado)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------
def _b64e(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def _b64d(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(mensagem: str) -> str:
    chave = get_settings().secret_key.encode()
    return _b64e(hmac.new(chave, mensagem.encode(), hashlib.sha256).digest())


def criar_token(usuario: dict) -> tuple[str, datetime]:
    expira = datetime.now(UTC) + timedelta(hours=get_settings().token_expiracao_horas)
    payload = {
        "sub": usuario["id"],
        "email": usuario["email"],
        "perfil": usuario["perfil"],
        "exp": int(expira.timestamp()),
    }
    corpo = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    return f"{corpo}.{_assinar(corpo)}", expira


def decodificar_token(token: str) -> dict:
    try:
        corpo, assinatura = token.split(".")
    except ValueError:
        raise _nao_autorizado("Token malformado")
    if not hmac.compare_digest(_assinar(corpo), assinatura):
        raise _nao_autorizado("Assinatura do token inválida")
    payload = json.loads(_b64d(corpo))
    if payload.get("exp", 0) < datetime.now(UTC).timestamp():
        raise _nao_autorizado("Token expirado")
    return payload


def _nao_autorizado(detalhe: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalhe,
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Dependências do FastAPI
# ---------------------------------------------------------------------------
def usuario_atual(
    credencial: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UsuarioOut:
    from app import repositories

    if credencial is None:
        raise _nao_autorizado("Credenciais não informadas")
    payload = decodificar_token(credencial.credentials)
    registro = repositories.usuarios().obter(payload["sub"])
    if registro is None or not registro.get("ativo", True):
        raise _nao_autorizado("Usuário inválido ou inativo")
    registro.pop("senha_hash", None)
    return UsuarioOut(**registro)


def requer_perfil(*perfis: Perfil):
    """Dependência que restringe a rota aos perfis informados."""

    permitidos = {Perfil(p) for p in perfis}

    def _checar(usuario: UsuarioOut = Depends(usuario_atual)) -> UsuarioOut:
        if usuario.perfil not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Perfil '{usuario.perfil}' não tem permissão para esta operação. "
                    f"Perfis permitidos: {', '.join(sorted(p.value for p in permitidos))}."
                ),
            )
        return usuario

    return _checar


# Atalhos usados pelos routers.
def apenas_gestao():
    return requer_perfil(Perfil.GERENTE, Perfil.ADMINISTRADOR)


def apenas_admin():
    return requer_perfil(Perfil.ADMINISTRADOR)


def qualquer_perfil():
    return requer_perfil(Perfil.MOTORISTA, Perfil.GERENTE, Perfil.ADMINISTRADOR)
