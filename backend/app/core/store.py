"""Abstração de persistência de documentos.

O back-end fala com o banco através da interface :class:`DocumentStore`.
Em produção a implementação usada é o Firestore (``app.core.firebase``);
a implementação em memória existe para rodar testes automatizados e para a
demonstração local sem credenciais (``FIRESTORE_BACKEND=memory``).

Convenção de tipos: tudo o que é gravado é primitivo (str, int, float, bool,
list, dict). Datas viram ``YYYY-MM-DD`` e instantes viram ISO-8601, o que
mantém as consultas por faixa funcionando igual nas duas implementações.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Iterable, Protocol

Filtro = tuple[str, str, Any]

OPERADORES = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a is not None and a >= b,
    "<=": lambda a, b: a is not None and a <= b,
    ">": lambda a, b: a is not None and a > b,
    "<": lambda a, b: a is not None and a < b,
    "in": lambda a, b: a in b,
}


class DocumentStore(Protocol):
    """Contrato mínimo de persistência usado pelos repositórios."""

    def criar(self, colecao: str, dados: dict, doc_id: str | None = None) -> dict: ...

    def obter(self, colecao: str, doc_id: str) -> dict | None: ...

    def listar(
        self,
        colecao: str,
        filtros: Iterable[Filtro] | None = None,
        ordenar_por: str | None = None,
        decrescente: bool = False,
        limite: int | None = None,
    ) -> list[dict]: ...

    def atualizar(self, colecao: str, doc_id: str, dados: dict) -> dict | None: ...

    def remover(self, colecao: str, doc_id: str) -> bool: ...


def novo_id() -> str:
    return uuid.uuid4().hex[:20]


def aplicar_filtros(registros: list[dict], filtros: Iterable[Filtro] | None) -> list[dict]:
    """Filtragem em memória, usada pelo MemoryStore e nos testes."""
    if not filtros:
        return registros
    resultado = []
    for reg in registros:
        if all(OPERADORES[op](reg.get(campo), valor) for campo, op, valor in filtros):
            resultado.append(reg)
    return resultado


class MemoryStore:
    """Implementação em memória do :class:`DocumentStore` (testes / demo)."""

    def __init__(self) -> None:
        self._dados: dict[str, dict[str, dict]] = {}
        self._lock = threading.RLock()

    def _colecao(self, colecao: str) -> dict[str, dict]:
        return self._dados.setdefault(colecao, {})

    def criar(self, colecao: str, dados: dict, doc_id: str | None = None) -> dict:
        with self._lock:
            doc_id = doc_id or novo_id()
            registro = {**dados, "id": doc_id}
            self._colecao(colecao)[doc_id] = registro
            return dict(registro)

    def obter(self, colecao: str, doc_id: str) -> dict | None:
        with self._lock:
            registro = self._colecao(colecao).get(doc_id)
            return dict(registro) if registro else None

    def listar(
        self,
        colecao: str,
        filtros: Iterable[Filtro] | None = None,
        ordenar_por: str | None = None,
        decrescente: bool = False,
        limite: int | None = None,
    ) -> list[dict]:
        with self._lock:
            registros = [dict(r) for r in self._colecao(colecao).values()]
        registros = aplicar_filtros(registros, filtros)
        if ordenar_por:
            registros.sort(
                key=lambda r: (r.get(ordenar_por) is None, r.get(ordenar_por)),
                reverse=decrescente,
            )
        if limite is not None:
            registros = registros[:limite]
        return registros

    def atualizar(self, colecao: str, doc_id: str, dados: dict) -> dict | None:
        with self._lock:
            registro = self._colecao(colecao).get(doc_id)
            if registro is None:
                return None
            registro.update(dados)
            registro["id"] = doc_id
            return dict(registro)

    def remover(self, colecao: str, doc_id: str) -> bool:
        with self._lock:
            return self._colecao(colecao).pop(doc_id, None) is not None

    def limpar(self) -> None:
        with self._lock:
            self._dados.clear()
