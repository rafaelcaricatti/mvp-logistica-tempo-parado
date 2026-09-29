"""RF12 — Exportação de relatórios do período consultado."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.core.security import qualquer_perfil
from app.schemas import Agrupamento, UsuarioOut
from app.services import relatorios as svc

router = APIRouter(prefix="/relatorios", tags=["RF12 · Relatórios"])


@router.get(
    "/historico.csv",
    response_class=PlainTextResponse,
    summary="Exporta o histórico do período em CSV",
)
def historico_csv(
    inicio: date | None = Query(default=None),
    fim: date | None = Query(default=None),
    motorista_id: str | None = None,
    usuario: UsuarioOut = Depends(qualquer_perfil()),
) -> PlainTextResponse:
    conteudo = svc.historico_csv(inicio, fim, motorista_id, usuario)
    nome = f"historico_{inicio or 'inicio'}_{fim or 'fim'}.csv"
    return PlainTextResponse(
        content=conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/completo", summary="Relatório consolidado do período (JSON)")
def completo(
    inicio: date | None = Query(default=None),
    fim: date | None = Query(default=None),
    motorista_id: str | None = None,
    agrupamento: Agrupamento = Agrupamento.DIA,
    usuario: UsuarioOut = Depends(qualquer_perfil()),
) -> dict:
    return svc.relatorio_completo(inicio, fim, motorista_id, agrupamento, usuario)
