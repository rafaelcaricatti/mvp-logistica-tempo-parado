"""Regras de negócio RN01 a RN07 e requisitos de cálculo RF06/RF11."""

from tests.conftest import marcar


def test_rn01_ponto_de_partida_nao_conta_tempo(client, admin, roteiro):
    """RN01 — o cronômetro só começa a valer a partir do segundo ponto."""
    atualizado = marcar(
        client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:40:00"
    )
    partida = atualizado["pontos"][0]
    assert partida["ponto_de_partida"] is True
    assert partida["tempo_parado_min"] == 0.0
    assert atualizado["tempo_total_parado_min"] == 0.0


def test_rn02_tempo_parado_e_saida_menos_chegada(client, admin, roteiro):
    """RN02 — tempo parado = saída - chegada."""
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:05:00")
    atualizado = marcar(
        client, admin, roteiro["id"], 2, "2026-03-10T08:30:00", "2026-03-10T08:45:00"
    )
    assert atualizado["pontos"][1]["tempo_parado_min"] == 15.0


def test_rn03_total_soma_tudo_menos_a_partida(client, admin, roteiro):
    """RN03 — total do roteiro A do exemplo: 15 + 10 + 50 = 75 min."""
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:10:00")
    marcar(client, admin, roteiro["id"], 2, "2026-03-10T08:30:00", "2026-03-10T08:45:00")
    marcar(client, admin, roteiro["id"], 3, "2026-03-10T09:00:00", "2026-03-10T09:10:00")
    final = marcar(
        client, admin, roteiro["id"], 4, "2026-03-10T09:30:00", "2026-03-10T10:20:00"
    )

    assert [p["tempo_parado_min"] for p in final["pontos"]] == [0.0, 15.0, 10.0, 50.0]
    assert final["tempo_total_parado_min"] == 75.0
    assert final["status"] == "concluido"


def test_rn04_percentual_da_jornada_de_8_horas(client, admin, roteiro):
    """RN04 — 75 min parados sobre jornada de 480 min = 15,62%."""
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:10:00")
    marcar(client, admin, roteiro["id"], 2, "2026-03-10T08:30:00", "2026-03-10T08:45:00")
    marcar(client, admin, roteiro["id"], 3, "2026-03-10T09:00:00", "2026-03-10T09:10:00")
    final = marcar(
        client, admin, roteiro["id"], 4, "2026-03-10T09:30:00", "2026-03-10T10:20:00"
    )
    assert round(final["percentual_jornada"] * 100, 2) == 15.62


def test_rn05_roteiro_tem_um_motorista_e_uma_data(client, roteiro, motorista):
    """RN05 — cada roteiro pertence a um único motorista e a uma única data."""
    assert roteiro["motorista_id"] == motorista["id"]
    assert roteiro["data"] == "2026-03-10"


def test_rn06_pontos_em_ordem_sequencial(client, roteiro):
    """RN06 — a ordem é atribuída automaticamente como 1, 2, 3, 4..."""
    assert [p["ordem"] for p in roteiro["pontos"]] == [1, 2, 3, 4]


def test_rn07_e_rf11_custo_do_trajeto(client, admin, roteiro):
    """RN07/RF11 — custo = combustível (distância/rendimento × R$/L) + custo por km."""
    detalhe = roteiro["custo_detalhado"]
    # 45,5 km ÷ 35 km/L = 1,3 L × R$ 5,85 = R$ 7,60 ; 45,5 km × R$ 1,20 = R$ 54,60
    assert detalhe["litros_estimados"] == 1.3
    assert detalhe["custo_combustivel"] == 7.60
    assert detalhe["custo_por_km_total"] == 54.60
    assert roteiro["custo_estimado"] == 62.20


def test_saida_antes_da_chegada_e_recusada(client, admin, roteiro):
    client.post(
        f"/roteiros/{roteiro['id']}/pontos/1/chegada",
        headers=admin,
        json={"horario": "2026-03-10T08:00:00"},
    )
    client.post(
        f"/roteiros/{roteiro['id']}/pontos/1/saida",
        headers=admin,
        json={"horario": "2026-03-10T08:05:00"},
    )
    client.post(
        f"/roteiros/{roteiro['id']}/pontos/2/chegada",
        headers=admin,
        json={"horario": "2026-03-10T09:00:00"},
    )
    resposta = client.post(
        f"/roteiros/{roteiro['id']}/pontos/2/saida",
        headers=admin,
        json={"horario": "2026-03-10T08:30:00"},
    )
    assert resposta.status_code == 422


def test_ordem_sequencial_e_exigida_na_coleta(client, admin, roteiro):
    """Não dá para chegar no ponto 3 sem ter saído do ponto 2 (RN06)."""
    resposta = client.post(f"/roteiros/{roteiro['id']}/pontos/3/chegada", headers=admin, json={})
    assert resposta.status_code == 409
