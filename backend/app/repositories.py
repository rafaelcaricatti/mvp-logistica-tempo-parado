"""Repositórios — acesso às coleções do Firestore.

Uma coleção por entidade do modelo de dados (seção 8 da especificação):

    motoristas, gerentes, pontos, roteiros, usuarios, auditoria, parametros
"""

from __future__ import annotations

from typing import Any, Iterable

from app.core.firebase import get_store
from app.core.store import DocumentStore, Filtro

COL_MOTORISTAS = "motoristas"
COL_GERENTES = "gerentes"
COL_PONTOS = "pontos"
COL_ROTEIROS = "roteiros"
COL_USUARIOS = "usuarios"
COL_AUDITORIA = "auditoria"
COL_PARAMETROS = "parametros"

# O documento de parâmetros é único e global (RF09/RF10).
DOC_PARAMETROS = "global"


class Repositorio:
    """CRUD genérico sobre uma coleção."""

    def __init__(self, colecao: str, store: DocumentStore | None = None) -> None:
        self.colecao = colecao
        self._store = store

    @property
    def store(self) -> DocumentStore:
        return self._store or get_store()

    def criar(self, dados: dict, doc_id: str | None = None) -> dict:
        return self.store.criar(self.colecao, dados, doc_id)

    def obter(self, doc_id: str) -> dict | None:
        return self.store.obter(self.colecao, doc_id)

    def listar(
        self,
        filtros: Iterable[Filtro] | None = None,
        ordenar_por: str | None = None,
        decrescente: bool = False,
        limite: int | None = None,
    ) -> list[dict]:
        return self.store.listar(self.colecao, filtros, ordenar_por, decrescente, limite)

    def atualizar(self, doc_id: str, dados: dict) -> dict | None:
        return self.store.atualizar(self.colecao, doc_id, dados)

    def remover(self, doc_id: str) -> bool:
        return self.store.remover(self.colecao, doc_id)

    def primeiro(self, filtros: Iterable[Filtro]) -> dict | None:
        encontrados = self.listar(filtros=filtros, limite=1)
        return encontrados[0] if encontrados else None


def motoristas() -> Repositorio:
    return Repositorio(COL_MOTORISTAS)


def gerentes() -> Repositorio:
    return Repositorio(COL_GERENTES)


def pontos() -> Repositorio:
    return Repositorio(COL_PONTOS)


def roteiros() -> Repositorio:
    return Repositorio(COL_ROTEIROS)


def usuarios() -> Repositorio:
    return Repositorio(COL_USUARIOS)


def auditoria() -> Repositorio:
    return Repositorio(COL_AUDITORIA)


def parametros() -> Repositorio:
    return Repositorio(COL_PARAMETROS)


def obter_parametros_raw() -> dict[str, Any] | None:
    return parametros().obter(DOC_PARAMETROS)


def salvar_parametros_raw(dados: dict[str, Any]) -> dict[str, Any]:
    repo = parametros()
    if repo.obter(DOC_PARAMETROS) is None:
        return repo.criar(dados, DOC_PARAMETROS)
    return repo.atualizar(DOC_PARAMETROS, dados) or dados
