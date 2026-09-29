"""Registro de auditoria das alterações (RNF05)."""

from __future__ import annotations

from datetime import UTC, datetime

from app import repositories
from app.schemas import AuditoriaOut, UsuarioOut


def registrar(
    acao: str,
    entidade: str,
    entidade_id: str | None = None,
    usuario: UsuarioOut | None = None,
    detalhes: dict | None = None,
) -> None:
    """Grava uma linha de auditoria. Nunca derruba a operação principal."""
    try:
        repositories.auditoria().criar(
            {
                "ocorrido_em": datetime.now(UTC).isoformat(),
                "usuario_id": usuario.id if usuario else None,
                "usuario_email": usuario.email if usuario else None,
                "perfil": str(usuario.perfil) if usuario else None,
                "acao": acao,
                "entidade": entidade,
                "entidade_id": entidade_id,
                "detalhes": detalhes or {},
            }
        )
    except Exception:  # pragma: no cover - auditoria é acessória
        import logging

        logging.getLogger(__name__).exception("Falha ao gravar auditoria de %s", acao)


def listar(
    entidade: str | None = None,
    entidade_id: str | None = None,
    limite: int = 200,
) -> list[AuditoriaOut]:
    filtros = []
    if entidade:
        filtros.append(("entidade", "==", entidade))
    if entidade_id:
        filtros.append(("entidade_id", "==", entidade_id))
    registros = repositories.auditoria().listar(
        filtros=filtros or None, ordenar_por="ocorrido_em", decrescente=True, limite=limite
    )
    return [AuditoriaOut(**r) for r in registros]
