"""Regras de negócio de tempo parado e de custo.

Implementa RN01 a RN07, RF06 (cálculo do tempo parado) e RF11 (custo estimado).
"""

from __future__ import annotations

from datetime import datetime

from app.schemas import CustoRoteiro, ParametrosOut, StatusParada, StatusRoteiro


def parse_horario(valor: str | datetime | None) -> datetime | None:
    if valor is None or isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(valor)


def arredondar(minutos: float, params: ParametrosOut) -> float:
    """Aplica a granularidade configurada em RF10."""
    passo = params.arredondamento_minutos
    if not passo:
        return round(minutos, 2)
    return round(round(minutos / passo) * passo, 2)


def tempo_parado_da_parada(
    chegada: datetime | str | None,
    saida: datetime | str | None,
    ordem: int,
    params: ParametrosOut,
) -> float | None:
    """RN01 + RN02 — tempo parado de um ponto.

    Devolve ``None`` enquanto a parada não estiver concluída, ``0.0`` no ponto
    de partida (salvo se o parâmetro ``contar_ponto_partida`` estiver ligado)
    e a diferença saída - chegada nos demais.
    """
    if ordem == 1 and not params.contar_ponto_partida:
        return 0.0  # RN01 — o ponto de partida não acumula tempo parado

    chegada, saida = parse_horario(chegada), parse_horario(saida)
    if chegada is None or saida is None:
        return None

    minutos = (saida - chegada).total_seconds() / 60.0
    if minutos < 0:
        raise ValueError("A saída não pode ser anterior à chegada.")
    if minutos < params.tolerancia_minutos:
        return 0.0
    return arredondar(minutos, params)


def status_da_parada(chegada, saida) -> StatusParada:
    if saida is not None:
        return StatusParada.CONCLUIDA
    if chegada is not None:
        return StatusParada.EM_ANDAMENTO
    return StatusParada.PENDENTE


def tempo_total_parado(paradas: list[dict], params: ParametrosOut) -> float:
    """RN03 — soma dos tempos parados, exceto o ponto de partida."""
    total = 0.0
    for parada in paradas:
        if parada.get("ordem") == 1 and not params.contar_ponto_partida:
            continue
        total += parada.get("tempo_parado_min") or 0.0
    return round(total, 2)


def calcular_custo(
    distancia_km: float, rendimento_km_l: float | None, params: ParametrosOut
) -> CustoRoteiro:
    """RN07 + RF11 — custo do trajeto a partir de combustível, km/l e distância."""
    rendimento = rendimento_km_l or params.rendimento_km_l_padrao
    litros = (distancia_km / rendimento) if rendimento else 0.0
    custo_combustivel = litros * params.valor_combustivel
    custo_km = distancia_km * params.custo_por_km
    return CustoRoteiro(
        litros_estimados=round(litros, 3),
        custo_combustivel=round(custo_combustivel, 2),
        custo_por_km_total=round(custo_km, 2),
        custo_total_estimado=round(custo_combustivel + custo_km, 2),
        valor_combustivel=params.valor_combustivel,
        rendimento_km_l=rendimento,
        custo_por_km=params.custo_por_km,
    )


def percentual_jornada(tempo_parado_min: float, params: ParametrosOut) -> float:
    """RN04 — tempo parado como fração da jornada padrão (8 h/dia)."""
    jornada_min = params.jornada_horas * 60
    if jornada_min <= 0:
        return 0.0
    return round(tempo_parado_min / jornada_min, 4)


def status_do_roteiro(paradas: list[dict]) -> StatusRoteiro:
    concluidas = sum(1 for p in paradas if p.get("saida"))
    iniciadas = sum(1 for p in paradas if p.get("chegada"))
    if concluidas == len(paradas) and paradas:
        return StatusRoteiro.CONCLUIDO
    if iniciadas:
        return StatusRoteiro.EM_ANDAMENTO
    return StatusRoteiro.PLANEJADO


def recalcular(roteiro: dict, params: ParametrosOut, rendimento_km_l: float | None) -> dict:
    """Recalcula tempos (RF06), status e custo (RF11) de um roteiro inteiro."""
    paradas = sorted(roteiro.get("pontos", []), key=lambda p: p["ordem"])
    for parada in paradas:
        parada["ponto_de_partida"] = parada["ordem"] == 1
        parada["tempo_parado_min"] = tempo_parado_da_parada(
            parada.get("chegada"), parada.get("saida"), parada["ordem"], params
        )
        parada["status"] = str(status_da_parada(parada.get("chegada"), parada.get("saida")))

    total = tempo_total_parado(paradas, params)
    custo = calcular_custo(
        roteiro.get("distancia_total_km", 0.0) or 0.0, rendimento_km_l, params
    )

    roteiro["pontos"] = paradas
    roteiro["tempo_total_parado_min"] = total
    roteiro["percentual_jornada"] = percentual_jornada(total, params)
    roteiro["custo_estimado"] = custo.custo_total_estimado
    roteiro["custo_detalhado"] = custo.model_dump()
    roteiro["status"] = str(status_do_roteiro(paradas))
    return roteiro
