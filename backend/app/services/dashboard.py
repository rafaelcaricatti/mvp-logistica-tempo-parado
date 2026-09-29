"""Histórico (RF07) e dashboard (RF08).

A agregação é feita em memória sobre os roteiros já filtrados por faixa de
data no Firestore, o que mantém a consulta de 12 meses dentro dos 3 segundos
exigidos pelo RNF03.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app import repositories
from app.schemas import (
    Agrupamento,
    DashboardOut,
    HistoricoOut,
    IndicadoresDashboard,
    ItemHistorico,
    Perfil,
    RankingItem,
    SerieItem,
    UsuarioOut,
)
from app.services import calculo, parametros as svc_parametros
from app.services import roteiros as svc_roteiros


def _periodo_padrao(inicio: date | None, fim: date | None) -> tuple[date, date]:
    hoje = date.today()
    fim = fim or hoje
    inicio = inicio or (fim - timedelta(days=29))
    if inicio > fim:
        inicio, fim = fim, inicio
    return inicio, fim


def _nomes_motoristas() -> dict[str, str]:
    return {m["id"]: m.get("nome", "—") for m in repositories.motoristas().listar()}


def _coletar(
    inicio: date, fim: date, motorista_id: str | None, usuario: UsuarioOut | None
) -> list[dict]:
    if usuario and usuario.perfil == Perfil.MOTORISTA:
        motorista_id = usuario.motorista_id
    params = svc_parametros.obter()
    nomes = _nomes_motoristas()
    rendimentos = {m["id"]: m.get("rendimento_km_l") for m in repositories.motoristas().listar()}

    registros = []
    for bruto in svc_roteiros.listar_raw(inicio, fim, motorista_id):
        calculado = calculo.recalcular(
            dict(bruto), params, rendimentos.get(bruto["motorista_id"])
        )
        calculado["motorista_nome"] = nomes.get(bruto["motorista_id"], "—")
        registros.append(calculado)
    return registros


# ---------------------------------------------------------------------------
# RF07 — histórico de pontos e tempos parados, com endereços
# ---------------------------------------------------------------------------
def historico(
    inicio: date | None = None,
    fim: date | None = None,
    motorista_id: str | None = None,
    somente_concluidos: bool = False,
    usuario: UsuarioOut | None = None,
) -> HistoricoOut:
    inicio, fim = _periodo_padrao(inicio, fim)
    itens: list[ItemHistorico] = []

    for roteiro in _coletar(inicio, fim, motorista_id, usuario):
        for parada in roteiro["pontos"]:
            if somente_concluidos and parada["status"] != "concluida":
                continue
            itens.append(
                ItemHistorico(
                    roteiro_id=roteiro["id"],
                    data=date.fromisoformat(roteiro["data"]),
                    motorista_id=roteiro["motorista_id"],
                    motorista_nome=roteiro.get("motorista_nome"),
                    ordem=parada["ordem"],
                    endereco=parada["endereco"],
                    latitude=parada.get("latitude"),
                    longitude=parada.get("longitude"),
                    chegada=calculo.parse_horario(parada.get("chegada")),
                    saida=calculo.parse_horario(parada.get("saida")),
                    tempo_parado_min=parada.get("tempo_parado_min") or 0.0,
                    ponto_de_partida=parada["ordem"] == 1,
                )
            )

    itens.sort(key=lambda i: (i.data, i.roteiro_id, i.ordem))
    total = round(sum(i.tempo_parado_min for i in itens if not i.ponto_de_partida), 2)
    return HistoricoOut(
        inicio=inicio,
        fim=fim,
        total_registros=len(itens),
        tempo_total_parado_min=total,
        itens=itens,
    )


# ---------------------------------------------------------------------------
# RF08 — dashboard por dia, por mês e por período
# ---------------------------------------------------------------------------
def dashboard(
    agrupamento: Agrupamento = Agrupamento.DIA,
    inicio: date | None = None,
    fim: date | None = None,
    motorista_id: str | None = None,
    usuario: UsuarioOut | None = None,
) -> DashboardOut:
    inicio, fim = _periodo_padrao(inicio, fim)
    params = svc_parametros.obter()
    roteiros = _coletar(inicio, fim, motorista_id, usuario)

    baldes: dict[str, dict] = defaultdict(
        lambda: {
            "tempo_parado_min": 0.0,
            "distancia_km": 0.0,
            "roteiros": 0,
            "paradas": 0,
            "custo_estimado": 0.0,
        }
    )
    por_endereco: dict[str, dict] = defaultdict(lambda: {"tempo": 0.0, "n": 0})
    por_motorista: dict[str, dict] = defaultdict(lambda: {"tempo": 0.0, "n": 0, "nome": "—"})

    total_paradas = 0
    paradas_com_tempo = 0

    for roteiro in roteiros:
        dia = date.fromisoformat(roteiro["data"])
        if agrupamento == Agrupamento.DIA:
            rotulo = dia.isoformat()
        elif agrupamento == Agrupamento.MES:
            rotulo = f"{dia.year:04d}-{dia.month:02d}"
        else:  # período inteiro em um único balde
            rotulo = f"{inicio.isoformat()} a {fim.isoformat()}"

        balde = baldes[rotulo]
        balde["tempo_parado_min"] += roteiro["tempo_total_parado_min"]
        balde["distancia_km"] += roteiro.get("distancia_total_km") or 0.0
        balde["roteiros"] += 1
        balde["custo_estimado"] += roteiro.get("custo_estimado") or 0.0

        mot = por_motorista[roteiro["motorista_id"]]
        mot["tempo"] += roteiro["tempo_total_parado_min"]
        mot["n"] += 1
        mot["nome"] = roteiro.get("motorista_nome") or "—"

        for parada in roteiro["pontos"]:
            if parada["ordem"] == 1 and not params.contar_ponto_partida:
                continue  # RN01
            total_paradas += 1
            balde["paradas"] += 1
            tempo = parada.get("tempo_parado_min") or 0.0
            if parada.get("saida"):
                paradas_com_tempo += 1
            end = por_endereco[parada["endereco"]]
            end["tempo"] += tempo
            end["n"] += 1

    serie = [
        SerieItem(
            rotulo=rotulo,
            tempo_parado_min=round(v["tempo_parado_min"], 2),
            distancia_km=round(v["distancia_km"], 2),
            roteiros=v["roteiros"],
            paradas=v["paradas"],
            custo_estimado=round(v["custo_estimado"], 2),
        )
        for rotulo, v in sorted(baldes.items())
    ]

    tempo_total = round(sum(s.tempo_parado_min for s in serie), 2)
    distancia_total = round(sum(s.distancia_km for s in serie), 2)
    custo_total = round(sum(s.custo_estimado for s in serie), 2)
    jornada_min = params.jornada_horas * 60

    indicadores = IndicadoresDashboard(
        tempo_total_parado_min=tempo_total,
        tempo_medio_por_parada_min=round(tempo_total / paradas_com_tempo, 2)
        if paradas_com_tempo
        else 0.0,
        distancia_total_km=distancia_total,
        total_roteiros=len(roteiros),
        total_paradas=total_paradas,
        custo_total_estimado=custo_total,
        jornada_horas=params.jornada_horas,
        jornadas_equivalentes=round(tempo_total / jornada_min, 2) if jornada_min else 0.0,
        percentual_jornada=round((tempo_total / jornada_min) * 100, 2) if jornada_min else 0.0,
    )

    ranking_enderecos = [
        RankingItem(chave=k, rotulo=k, tempo_parado_min=round(v["tempo"], 2), ocorrencias=v["n"])
        for k, v in sorted(por_endereco.items(), key=lambda kv: -kv[1]["tempo"])[:10]
    ]
    ranking_motoristas = [
        RankingItem(
            chave=k, rotulo=v["nome"], tempo_parado_min=round(v["tempo"], 2), ocorrencias=v["n"]
        )
        for k, v in sorted(por_motorista.items(), key=lambda kv: -kv[1]["tempo"])[:10]
    ]

    return DashboardOut(
        agrupamento=agrupamento,
        inicio=inicio,
        fim=fim,
        motorista_id=motorista_id,
        serie=serie,
        indicadores=indicadores,
        ranking_enderecos=ranking_enderecos,
        ranking_motoristas=ranking_motoristas,
    )
