"""Serviço de roteiros: montagem (RF04), coleta (RF05) e cálculo (RF06/RF11)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import HTTPException, status

from app import repositories
from app.schemas import (
    ParadaCreate,
    Perfil,
    RoteiroCreate,
    RoteiroOut,
    RoteiroUpdate,
    UsuarioOut,
)
from app.services import auditoria, calculo, parametros as svc_parametros


# Starlette renomeou a constante 422; o getattr mantém compatibilidade com
# as duas versões.
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _erro(codigo: int, detalhe: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=detalhe)


def _motorista_ou_404(motorista_id: str) -> dict:
    motorista = repositories.motoristas().obter(motorista_id)
    if motorista is None:
        raise _erro(status.HTTP_404_NOT_FOUND, f"Motorista '{motorista_id}' não encontrado.")
    return motorista


def _resolver_paradas(pontos: list[ParadaCreate]) -> list[dict]:
    """RN06 — numera os pontos em ordem sequencial e resolve endereços."""
    repo_pontos = repositories.pontos()
    paradas: list[dict] = []
    for indice, entrada in enumerate(pontos, start=1):
        endereco = entrada.endereco
        latitude, longitude = entrada.latitude, entrada.longitude

        if entrada.ponto_id:
            cadastro = repo_pontos.obter(entrada.ponto_id)
            if cadastro is None:
                raise _erro(
                    status.HTTP_404_NOT_FOUND, f"Ponto '{entrada.ponto_id}' não cadastrado."
                )
            endereco = endereco or cadastro["endereco"]
            latitude = latitude if latitude is not None else cadastro.get("latitude")
            longitude = longitude if longitude is not None else cadastro.get("longitude")

        if not endereco:
            raise _erro(
                HTTP_422,
                f"O ponto {indice} precisa de um endereço ou de um ponto_id cadastrado.",
            )

        paradas.append(
            {
                "ordem": indice,
                "ponto_id": entrada.ponto_id,
                "endereco": endereco,
                "latitude": latitude,
                "longitude": longitude,
                "chegada": None,
                "saida": None,
                "tempo_parado_min": 0.0 if indice == 1 else None,
                "ponto_de_partida": indice == 1,
                "status": "pendente",
                "observacao": entrada.observacao,
            }
        )
    return paradas


def _montar_saida(registro: dict) -> RoteiroOut:
    params = svc_parametros.obter()
    motorista = repositories.motoristas().obter(registro["motorista_id"])
    calculado = calculo.recalcular(
        dict(registro), params, (motorista or {}).get("rendimento_km_l")
    )
    calculado["motorista_nome"] = (motorista or {}).get("nome")
    return RoteiroOut(**calculado)


def _persistir_calculo(registro: dict) -> dict:
    """Recalcula e grava os campos derivados (RF06/RF11) no Firestore."""
    params = svc_parametros.obter()
    motorista = repositories.motoristas().obter(registro["motorista_id"])
    calculado = calculo.recalcular(
        dict(registro), params, (motorista or {}).get("rendimento_km_l")
    )
    atualizacao = {
        "pontos": calculado["pontos"],
        "tempo_total_parado_min": calculado["tempo_total_parado_min"],
        "percentual_jornada": calculado["percentual_jornada"],
        "custo_estimado": calculado["custo_estimado"],
        "custo_detalhado": calculado["custo_detalhado"],
        "status": calculado["status"],
        "atualizado_em": datetime.now(UTC).isoformat(),
    }
    repositories.roteiros().atualizar(registro["id"], atualizacao)
    return {**registro, **atualizacao}


def checar_acesso(registro: dict, usuario: UsuarioOut) -> None:
    """RNF04 — motorista só enxerga/mexe nos próprios roteiros."""
    if usuario.perfil == Perfil.MOTORISTA and registro["motorista_id"] != usuario.motorista_id:
        raise _erro(
            status.HTTP_403_FORBIDDEN,
            "Este roteiro pertence a outro motorista.",
        )


# ---------------------------------------------------------------------------
# Operações
# ---------------------------------------------------------------------------
def criar(payload: RoteiroCreate, usuario: UsuarioOut | None = None) -> RoteiroOut:
    _motorista_ou_404(payload.motorista_id)
    paradas = _resolver_paradas(payload.pontos)
    agora = datetime.now(UTC).isoformat()

    registro = repositories.roteiros().criar(
        {
            "data": payload.data.isoformat(),  # RN05 — uma única data
            "motorista_id": payload.motorista_id,  # RN05 — um único motorista
            "distancia_total_km": payload.distancia_total_km,
            "pontos": paradas,
            "observacao": payload.observacao,
            "status": "planejado",
            "tempo_total_parado_min": 0.0,
            "percentual_jornada": 0.0,
            "custo_estimado": 0.0,
            "criado_em": agora,
            "atualizado_em": agora,
        }
    )
    registro = _persistir_calculo(registro)
    auditoria.registrar(
        "criar", "roteiro", registro["id"], usuario, {"pontos": len(paradas)}
    )
    return _montar_saida(registro)


def obter(roteiro_id: str) -> RoteiroOut:
    registro = obter_raw(roteiro_id)
    return _montar_saida(registro)


def obter_raw(roteiro_id: str) -> dict:
    registro = repositories.roteiros().obter(roteiro_id)
    if registro is None:
        raise _erro(status.HTTP_404_NOT_FOUND, f"Roteiro '{roteiro_id}' não encontrado.")
    return registro


def listar_raw(
    inicio: date | None = None,
    fim: date | None = None,
    motorista_id: str | None = None,
) -> list[dict]:
    filtros: list[tuple] = []
    if motorista_id:
        filtros.append(("motorista_id", "==", motorista_id))
    if inicio:
        filtros.append(("data", ">=", inicio.isoformat()))
    if fim:
        filtros.append(("data", "<=", fim.isoformat()))
    return repositories.roteiros().listar(filtros=filtros or None, ordenar_por="data")


def listar(
    inicio: date | None = None,
    fim: date | None = None,
    motorista_id: str | None = None,
    usuario: UsuarioOut | None = None,
) -> list[RoteiroOut]:
    if usuario and usuario.perfil == Perfil.MOTORISTA:
        motorista_id = usuario.motorista_id
    registros = listar_raw(inicio, fim, motorista_id)
    return [_montar_saida(r) for r in registros]


def atualizar(
    roteiro_id: str, payload: RoteiroUpdate, usuario: UsuarioOut | None = None
) -> RoteiroOut:
    registro = obter_raw(roteiro_id)
    mudancas = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "data" in mudancas:
        mudancas["data"] = payload.data.isoformat()
    if "motorista_id" in mudancas:
        _motorista_ou_404(mudancas["motorista_id"])
    mudancas["atualizado_em"] = datetime.now(UTC).isoformat()
    repositories.roteiros().atualizar(roteiro_id, mudancas)

    registro = _persistir_calculo({**registro, **mudancas})
    auditoria.registrar("atualizar", "roteiro", roteiro_id, usuario, {"mudancas": mudancas})
    return _montar_saida(registro)


def remover(roteiro_id: str, usuario: UsuarioOut | None = None) -> None:
    obter_raw(roteiro_id)
    repositories.roteiros().remover(roteiro_id)
    auditoria.registrar("remover", "roteiro", roteiro_id, usuario)


def adicionar_parada(
    roteiro_id: str, parada: ParadaCreate, usuario: UsuarioOut | None = None
) -> RoteiroOut:
    registro = obter_raw(roteiro_id)
    paradas = list(registro.get("pontos", []))
    nova = _resolver_paradas([parada])[0]
    nova["ordem"] = len(paradas) + 1
    nova["ponto_de_partida"] = nova["ordem"] == 1
    nova["tempo_parado_min"] = 0.0 if nova["ordem"] == 1 else None
    paradas.append(nova)
    registro["pontos"] = paradas
    repositories.roteiros().atualizar(roteiro_id, {"pontos": paradas})
    registro = _persistir_calculo(registro)
    auditoria.registrar(
        "adicionar_parada", "roteiro", roteiro_id, usuario, {"ordem": nova["ordem"]}
    )
    return _montar_saida(registro)


def _registrar_marcacao(
    roteiro_id: str,
    ordem: int,
    campo: str,
    horario: datetime | None,
    usuario: UsuarioOut | None,
) -> RoteiroOut:
    registro = obter_raw(roteiro_id)
    if usuario:
        checar_acesso(registro, usuario)

    paradas = registro.get("pontos", [])
    parada = next((p for p in paradas if p["ordem"] == ordem), None)
    if parada is None:
        raise _erro(
            status.HTTP_404_NOT_FOUND, f"Ponto de ordem {ordem} não existe neste roteiro."
        )

    instante = horario or datetime.now().astimezone()

    if campo == "chegada":
        if parada.get("chegada"):
            raise _erro(
                status.HTTP_409_CONFLICT, f"A chegada no ponto {ordem} já foi registrada."
            )
        anterior = next((p for p in paradas if p["ordem"] == ordem - 1), None)
        if anterior is not None and not anterior.get("saida"):
            raise _erro(
                status.HTTP_409_CONFLICT,
                f"Registre a saída do ponto {ordem - 1} antes de chegar no ponto {ordem}. "
                "Os pontos seguem a ordem sequencial do roteiro (RN06).",
            )
    else:  # saida
        if not parada.get("chegada"):
            raise _erro(
                status.HTTP_409_CONFLICT,
                f"Registre a chegada no ponto {ordem} antes da saída.",
            )
        if parada.get("saida"):
            raise _erro(
                status.HTTP_409_CONFLICT, f"A saída do ponto {ordem} já foi registrada."
            )
        if instante < calculo.parse_horario(parada["chegada"]):
            raise _erro(
                HTTP_422,
                "O horário de saída não pode ser anterior ao de chegada (RN02).",
            )

    valor_anterior = parada.get(campo)
    parada[campo] = instante.isoformat()
    registro["pontos"] = paradas
    repositories.roteiros().atualizar(roteiro_id, {"pontos": paradas})
    registro = _persistir_calculo(registro)

    # RNF05 — toda marcação de horário fica auditada.
    auditoria.registrar(
        f"registrar_{campo}",
        "roteiro",
        roteiro_id,
        usuario,
        {
            "ordem": ordem,
            "endereco": parada["endereco"],
            "valor_anterior": valor_anterior,
            "valor_novo": parada[campo],
        },
    )
    return _montar_saida(registro)


def registrar_chegada(
    roteiro_id: str, ordem: int, horario: datetime | None, usuario: UsuarioOut | None = None
) -> RoteiroOut:
    return _registrar_marcacao(roteiro_id, ordem, "chegada", horario, usuario)


def registrar_saida(
    roteiro_id: str, ordem: int, horario: datetime | None, usuario: UsuarioOut | None = None
) -> RoteiroOut:
    return _registrar_marcacao(roteiro_id, ordem, "saida", horario, usuario)
