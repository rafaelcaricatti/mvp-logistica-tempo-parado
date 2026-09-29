"""Parâmetros de custo e de cálculo (RF09, RF10, RN04, RN07).

São lidos do Firestore em um documento único, de modo que o critério de
aceitação "os parâmetros de custo e de jornada podem ser alterados sem
alteração de código" seja atendido.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app import repositories
from app.schemas import ParametrosBase, ParametrosOut, ParametrosUpdate, UsuarioOut

PADRAO = ParametrosBase(
    valor_combustivel=5.85,
    custo_por_km=1.20,
    rendimento_km_l_padrao=12.0,
    jornada_horas=8.0,  # RN04
    contar_ponto_partida=False,  # RN01
    tolerancia_minutos=0.0,
    arredondamento_minutos=1,
)


def obter() -> ParametrosOut:
    registro = repositories.obter_parametros_raw()
    if registro is None:
        return ParametrosOut(**PADRAO.model_dump())
    dados = {**PADRAO.model_dump(), **registro}
    dados.pop("id", None)
    return ParametrosOut(**dados)


def garantir_padrao() -> ParametrosOut:
    """Cria o documento de parâmetros na primeira execução."""
    if repositories.obter_parametros_raw() is None:
        repositories.salvar_parametros_raw(
            {**PADRAO.model_dump(), "atualizado_em": datetime.now(UTC).isoformat()}
        )
    return obter()


def atualizar(payload: ParametrosUpdate, usuario: UsuarioOut | None = None) -> ParametrosOut:
    atuais = obter().model_dump()
    mudancas = payload.model_dump(exclude_unset=True, exclude_none=True)
    atuais.update(mudancas)
    atuais["atualizado_em"] = datetime.now(UTC).isoformat()
    atuais["atualizado_por"] = usuario.email if usuario else None
    repositories.salvar_parametros_raw(atuais)

    from app.services import auditoria

    auditoria.registrar("atualizar", "parametros", "global", usuario, {"mudancas": mudancas})
    return obter()
