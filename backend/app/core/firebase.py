"""Inicialização do Firebase e implementação Firestore do DocumentStore."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Iterable

from app.core.config import get_settings
from app.core.store import DocumentStore, Filtro, MemoryStore, novo_id

logger = logging.getLogger(__name__)


class FirestoreStore:
    """Persistência em Cloud Firestore via SDK ``firebase-admin``."""

    def __init__(self, client, prefixo: str = "") -> None:
        self._db = client
        self._prefixo = prefixo

    def _col(self, colecao: str):
        return self._db.collection(f"{self._prefixo}{colecao}")

    def criar(self, colecao: str, dados: dict, doc_id: str | None = None) -> dict:
        doc_id = doc_id or novo_id()
        registro = {**dados, "id": doc_id}
        self._col(colecao).document(doc_id).set(registro)
        return registro

    def obter(self, colecao: str, doc_id: str) -> dict | None:
        snap = self._col(colecao).document(doc_id).get()
        if not snap.exists:
            return None
        return {**snap.to_dict(), "id": snap.id}

    def listar(
        self,
        colecao: str,
        filtros: Iterable[Filtro] | None = None,
        ordenar_por: str | None = None,
        decrescente: bool = False,
        limite: int | None = None,
    ) -> list[dict]:
        from google.cloud.firestore_v1.base_query import FieldFilter

        consulta = self._col(colecao)
        for campo, operador, valor in filtros or []:
            consulta = consulta.where(filter=FieldFilter(campo, operador, valor))
        if ordenar_por:
            direcao = "DESCENDING" if decrescente else "ASCENDING"
            consulta = consulta.order_by(ordenar_por, direction=direcao)
        if limite is not None:
            consulta = consulta.limit(limite)
        return [{**doc.to_dict(), "id": doc.id} for doc in consulta.stream()]

    def atualizar(self, colecao: str, doc_id: str, dados: dict) -> dict | None:
        ref = self._col(colecao).document(doc_id)
        if not ref.get().exists:
            return None
        ref.update(dados)
        return self.obter(colecao, doc_id)

    def remover(self, colecao: str, doc_id: str) -> bool:
        ref = self._col(colecao).document(doc_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True


def _tem_credencial_explicita() -> bool:
    cfg = get_settings()
    return bool(
        cfg.firebase_credentials_json
        or cfg.firebase_credentials_file
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )


def _credencial():
    """Resolve a credencial do Firebase a partir das configurações."""
    from firebase_admin import credentials

    cfg = get_settings()

    if cfg.firebase_credentials_json:
        return credentials.Certificate(json.loads(cfg.firebase_credentials_json))

    if cfg.firebase_credentials_file:
        caminho = os.path.expanduser(cfg.firebase_credentials_file)
        if not os.path.exists(caminho):
            raise FileNotFoundError(
                f"Arquivo de credenciais do Firebase não encontrado: {caminho}"
            )
        return credentials.Certificate(caminho)

    # Credenciais Padrão do Google (ADC): cobre GOOGLE_APPLICATION_CREDENTIALS,
    # `gcloud auth application-default login` e, o caso mais importante em produção,
    # a service account anexada automaticamente ao rodar em Cloud Run/GCE/Cloud
    # Functions — nesse caso nenhuma variável de ambiente precisa ser definida.
    return credentials.ApplicationDefault()


def _client_emulador():
    """Cliente Firestore apontado para o emulador local (sem credencial real)."""
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore as gcf

    cfg = get_settings()
    projeto = cfg.firebase_project_id or os.getenv("GCLOUD_PROJECT") or "demo-parouai"
    logger.info(
        "Conectando ao emulador do Firestore em %s (projeto %s)",
        os.getenv("FIRESTORE_EMULATOR_HOST"),
        projeto,
    )
    return gcf.Client(project=projeto, credentials=AnonymousCredentials())


def _criar_firestore_store() -> FirestoreStore:
    import firebase_admin
    from firebase_admin import firestore

    cfg = get_settings()

    if os.getenv("FIRESTORE_EMULATOR_HOST") and not _tem_credencial_explicita():
        return FirestoreStore(_client_emulador(), cfg.firestore_prefix)

    if not firebase_admin._apps:
        opcoes = {"projectId": cfg.firebase_project_id} if cfg.firebase_project_id else None
        firebase_admin.initialize_app(_credencial(), opcoes)
    return FirestoreStore(firestore.client(), cfg.firestore_prefix)


@lru_cache
def get_store() -> DocumentStore:
    """Devolve o store configurado (Firestore por padrão).

    ``FIRESTORE_BACKEND=memory`` troca para a implementação em memória — usada
    pelos testes automatizados e pela demonstração sem credenciais.
    """
    backend = os.getenv("FIRESTORE_BACKEND", "firestore").lower()
    if backend == "memory":
        logger.warning("Persistência em MEMÓRIA ativa: os dados somem ao reiniciar a API.")
        return MemoryStore()
    return _criar_firestore_store()


def resetar_store() -> None:
    """Limpa o cache do store (usado nos testes)."""
    get_store.cache_clear()
