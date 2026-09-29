"""RF12 — exportação de relatórios do período consultado (CSV e JSON)."""

from __future__ import annotations

import csv
import io
import json
from datetime import date

from app.schemas import Agrupamento, UsuarioOut
from app.services import dashboard as svc_dashboard

COLUNAS_HISTORICO = [
    "data",
    "roteiro_id",
    "motorista",
    "ordem",
    "endereco",
    "latitude",
    "longitude",
    "chegada",
    "saida",
    "tempo_parado_min",
    "ponto_de_partida",
]


def _iso(valor) -> str:
    return valor.isoformat() if valor is not None else ""


def historico_csv(
    inicio: date | None,
    fim: date | None,
    motorista_id: str | None,
    usuario: UsuarioOut | None = None,
) -> str:
    dados = svc_dashboard.historico(inicio, fim, motorista_id, usuario=usuario)
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(COLUNAS_HISTORICO)
    for item in dados.itens:
        escritor.writerow(
            [
                item.data.isoformat(),
                item.roteiro_id,
                item.motorista_nome or item.motorista_id,
                item.ordem,
                item.endereco,
                item.latitude if item.latitude is not None else "",
                item.longitude if item.longitude is not None else "",
                _iso(item.chegada),
                _iso(item.saida),
                f"{item.tempo_parado_min:.2f}".replace(".", ","),
                "sim" if item.ponto_de_partida else "não",
            ]
        )
    escritor.writerow([])
    escritor.writerow(
        ["TOTAL", "", "", "", "", "", "", "", "", f"{dados.tempo_total_parado_min:.2f}".replace(".", ","), ""]
    )
    return buffer.getvalue()


def relatorio_completo(
    inicio: date | None,
    fim: date | None,
    motorista_id: str | None,
    agrupamento: Agrupamento = Agrupamento.DIA,
    usuario: UsuarioOut | None = None,
) -> dict:
    painel = svc_dashboard.dashboard(agrupamento, inicio, fim, motorista_id, usuario=usuario)
    historico = svc_dashboard.historico(inicio, fim, motorista_id, usuario=usuario)
    return {
        "periodo": {"inicio": painel.inicio.isoformat(), "fim": painel.fim.isoformat()},
        "agrupamento": str(painel.agrupamento),
        "motorista_id": motorista_id,
        "indicadores": painel.indicadores.model_dump(),
        "serie": [s.model_dump() for s in painel.serie],
        "ranking_enderecos": [r.model_dump() for r in painel.ranking_enderecos],
        "ranking_motoristas": [r.model_dump() for r in painel.ranking_motoristas],
        "historico": json.loads(historico.model_dump_json())["itens"],
    }
