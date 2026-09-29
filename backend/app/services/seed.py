"""Carga inicial: parâmetros, usuários e (opcionalmente) dados de demonstração.

Os roteiros A, B e C reproduzem o exemplo da seção 5 da especificação; o
restante é histórico sintético para o dashboard ter o que mostrar.
"""

from __future__ import annotations

import logging
import random
from datetime import date, datetime, time, timedelta

from app import repositories
from app.schemas import (
    GerenteCreate,
    MotoristaCreate,
    ParadaCreate,
    Perfil,
    PontoCreate,
    RoteiroCreate,
    UsuarioCreate,
)
from app.services import roteiros as svc_roteiros
from app.services import parametros as svc_parametros
from app.services import usuarios as svc_usuarios

logger = logging.getLogger(__name__)

# Exemplo da seção 5 da especificação (roteiro / endereço / tempo parado).
ROTEIROS_EXEMPLO = [
    ("A", ["Seg. Família (partida)", "Rua Peru, 55", "Rua X, 5", "Av. João César"], [0, 15, 10, 50]),
    ("B", ["Partida", "Ponto B2", "Ponto B3", "Ponto B4"], [0, 10, 5, 26]),
    ("C", ["Partida", "Ponto C2", "Ponto C3", "Ponto C4"], [0, 5, 10, 30]),
]

MOTORISTAS_DEMO = [
    MotoristaCreate(
        nome="Carlos Silva",
        telefone="(31) 99999-0001",
        documento="123.456.789-00",
        veiculo="Moto Honda CG 160",
        rendimento_km_l=35.0,
    ),
    MotoristaCreate(
        nome="João Pereira",
        telefone="(31) 99999-0002",
        documento="987.654.321-00",
        veiculo="Fiorino",
        rendimento_km_l=10.5,
    ),
    MotoristaCreate(
        nome="Marina Souza",
        telefone="(31) 99999-0003",
        documento="456.123.789-00",
        veiculo="Renault Kangoo",
        rendimento_km_l=11.8,
    ),
]

PONTOS_DEMO = [
    PontoCreate(apelido="CD Seg. Família", endereco="Rua Seg. Família, 10 - Belo Horizonte/MG",
                latitude=-19.9245, longitude=-43.9352),
    PontoCreate(apelido="Cliente Peru", endereco="Rua Peru, 55 - Belo Horizonte/MG",
                latitude=-19.9318, longitude=-43.9401),
    PontoCreate(apelido="Cliente X", endereco="Rua X, 5 - Contagem/MG",
                latitude=-19.9105, longitude=-44.0536),
    PontoCreate(apelido="Cliente João César", endereco="Av. João César, 1200 - Belo Horizonte/MG",
                latitude=-19.8570, longitude=-43.9600),
    PontoCreate(apelido="Cliente Sabará", endereco="Av. Brasil, 340 - Sabará/MG",
                latitude=-19.8899, longitude=-43.8064),
]


def _base_vazia() -> bool:
    return not repositories.motoristas().listar(limite=1)


def _marcar_horarios(roteiro_id: str, dia: date, tempos: list[int], inicio_hora: int = 8) -> None:
    """Preenche chegada/saída de forma que o tempo parado caia no valor desejado.

    Os tempos nunca são gravados direto: são sempre derivados de chegada/saída
    pelo serviço de cálculo (RN02), como acontece no uso real.
    """
    relogio = datetime.combine(dia, time(hour=inicio_hora, minute=0))
    for ordem, minutos in enumerate(tempos, start=1):
        svc_roteiros.registrar_chegada(roteiro_id, ordem, relogio.astimezone())
        relogio += timedelta(minutes=minutos)
        svc_roteiros.registrar_saida(roteiro_id, ordem, relogio.astimezone())
        relogio += timedelta(minutes=random.randint(12, 28))  # deslocamento até o próximo ponto


def executar(com_demo: bool = True, dias_historico: int = 120, semente: int = 42) -> dict:
    """Roda a carga inicial e devolve um resumo do que foi criado."""
    from app.core.config import get_settings

    cfg = get_settings()
    resumo: dict[str, int | str] = {}

    svc_parametros.garantir_padrao()
    svc_usuarios.garantir_admin(cfg.admin_email, cfg.admin_senha)
    resumo["admin"] = cfg.admin_email

    if not com_demo:
        return resumo

    if not _base_vazia():
        resumo["demo"] = "ignorada (já existem motoristas cadastrados)"
        return resumo

    random.seed(semente)

    motoristas = [repositories.motoristas().criar(m.model_dump()) for m in MOTORISTAS_DEMO]
    pontos = [repositories.pontos().criar(p.model_dump()) for p in PONTOS_DEMO]
    resumo["motoristas"] = len(motoristas)
    resumo["pontos"] = len(pontos)

    gerente = repositories.gerentes().criar(
        GerenteCreate(
            nome="Ana Coordenadora",
            telefone="(31) 98888-1000",
            email="ana@parouai.com",
            equipe=[m["id"] for m in motoristas],
        ).model_dump()
    )
    resumo["gerentes"] = 1

    svc_usuarios.criar(
        UsuarioCreate(
            nome="Ana Coordenadora",
            email="gerente@parouai.com",
            senha="gerente123",
            perfil=Perfil.GERENTE,
            gerente_id=gerente["id"],
        )
    )
    svc_usuarios.criar(
        UsuarioCreate(
            nome=motoristas[0]["nome"],
            email="motorista@parouai.com",
            senha="motorista123",
            perfil=Perfil.MOTORISTA,
            motorista_id=motoristas[0]["id"],
        )
    )
    resumo["usuarios"] = 3

    hoje = date.today()
    criados = 0

    # 1) Os três roteiros do exemplo da especificação, no dia anterior.
    for indice, (_, enderecos, tempos) in enumerate(ROTEIROS_EXEMPLO):
        roteiro = svc_roteiros.criar(
            RoteiroCreate(
                data=hoje - timedelta(days=1),
                motorista_id=motoristas[indice % len(motoristas)]["id"],
                distancia_total_km=round(random.uniform(35, 60), 1),
                pontos=[ParadaCreate(endereco=e) for e in enderecos],
                observacao="Roteiro de exemplo da especificação (seção 5).",
            )
        )
        _marcar_horarios(roteiro.id, hoje - timedelta(days=1), tempos, inicio_hora=7 + indice)
        criados += 1

    # 2) Histórico sintético para os gráficos por dia / mês / período.
    for dias_atras in range(2, dias_historico + 2):
        dia = hoje - timedelta(days=dias_atras)
        if dia.weekday() == 6:  # domingo sem operação
            continue
        for motorista in random.sample(motoristas, k=random.randint(1, len(motoristas))):
            n_pontos = random.randint(3, 5)
            escolhidos = random.sample(pontos, k=min(n_pontos, len(pontos)))
            roteiro = svc_roteiros.criar(
                RoteiroCreate(
                    data=dia,
                    motorista_id=motorista["id"],
                    distancia_total_km=round(random.uniform(20, 85), 1),
                    pontos=[ParadaCreate(ponto_id=p["id"]) for p in escolhidos],
                )
            )
            tempos = [0] + [max(3, int(random.gauss(22, 9))) for _ in escolhidos[1:]]
            _marcar_horarios(roteiro.id, dia, tempos, inicio_hora=random.randint(7, 9))
            criados += 1

    # 3) Um roteiro em aberto para hoje, para demonstrar a coleta (RF05).
    svc_roteiros.criar(
        RoteiroCreate(
            data=hoje,
            motorista_id=motoristas[0]["id"],
            distancia_total_km=45.5,
            pontos=[
                ParadaCreate(ponto_id=pontos[0]["id"]),
                ParadaCreate(ponto_id=pontos[1]["id"]),
                ParadaCreate(ponto_id=pontos[2]["id"]),
                ParadaCreate(ponto_id=pontos[3]["id"]),
            ],
            observacao="Roteiro do dia — aguardando registro de chegada/saída.",
        )
    )
    criados += 1

    resumo["roteiros"] = criados
    logger.info("Carga de demonstração concluída: %s", resumo)
    return resumo
