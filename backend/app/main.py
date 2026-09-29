"""API REST do MVP de Monitoramento de Tempo Parado em Roteiros.

Sobe com:  uvicorn app.main:app --reload --port 8000
Documentação interativa em  http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    admin,
    auditoria,
    auth,
    dashboard,
    gerentes,
    motoristas,
    parametros,
    pontos,
    relatorios,
    roteiros,
    usuarios,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s | %(message)s"
)
logger = logging.getLogger("parouai")

DESCRICAO = """
API do MVP **Sistema de Monitoramento de Tempo Parado em Roteiros**.

Cobre os requisitos funcionais RF01 a RF12 da Especificação de Requisitos e
persiste tudo no **Cloud Firestore (Firebase)**.

**Autenticação:** `POST /auth/login` devolve um token *bearer*. Clique em
*Authorize* aqui no Swagger e cole o token para testar as rotas protegidas.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    logger.info("Iniciando %s v%s", cfg.app_name, cfg.app_version)
    try:
        from app.services import parametros as svc_parametros
        from app.services import usuarios as svc_usuarios

        svc_parametros.garantir_padrao()
        svc_usuarios.garantir_admin(cfg.admin_email, cfg.admin_senha)
        logger.info("Persistência pronta. Administrador: %s", cfg.admin_email)
    except Exception:
        logger.exception(
            "Não foi possível preparar a persistência. Confira as credenciais do Firebase "
            "no arquivo .env (veja o README)."
        )
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=DESCRICAO,
    lifespan=lifespan,
    swagger_ui_parameters={"docExpansion": "none"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def medir_tempo(request: Request, call_next):
    """RNF03 — expõe o tempo de resposta para conferência do limite de 3 s."""
    inicio = time.perf_counter()
    resposta = await call_next(request)
    decorrido_ms = (time.perf_counter() - inicio) * 1000
    resposta.headers["X-Tempo-Resposta-ms"] = f"{decorrido_ms:.1f}"
    if decorrido_ms > 3000:
        logger.warning("Resposta acima de 3 s: %s %s (%.0f ms)", request.method, request.url.path, decorrido_ms)
    return resposta


@app.get("/", tags=["Infra"], summary="Identificação da API")
def raiz() -> dict:
    return {
        "aplicacao": settings.app_name,
        "versao": settings.app_version,
        "documentacao": "/docs",
        "saude": "/health",
    }


@app.get("/health", tags=["Infra"], summary="Verifica a conexão com o banco")
def health() -> dict:
    from app import repositories

    try:
        repositories.parametros().listar(limite=1)
        return {"status": "ok", "persistencia": "conectada"}
    except Exception as erro:  # pragma: no cover
        return {"status": "degradado", "persistencia": "indisponível", "erro": str(erro)}


for modulo in (
    auth,
    usuarios,
    motoristas,
    gerentes,
    pontos,
    roteiros,
    dashboard,
    parametros,
    relatorios,
    auditoria,
    admin,
):
    app.include_router(modulo.router)
