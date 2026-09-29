"""Requisitos não funcionais: persistência, acesso por perfil, auditoria e desempenho."""

import time

from tests.conftest import marcar


def test_rnf01_dados_persistem_entre_requisicoes(client, admin, roteiro):
    """RNF01 — o roteiro gravado continua disponível em uma nova consulta."""
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:05:00")
    marcar(client, admin, roteiro["id"], 2, "2026-03-10T08:20:00", "2026-03-10T08:32:00")

    relido = client.get(f"/roteiros/{roteiro['id']}", headers=admin).json()
    assert relido["tempo_total_parado_min"] == 12.0
    assert relido["pontos"][1]["chegada"] is not None


def test_rnf04_rota_protegida_exige_token(client):
    assert client.get("/motoristas").status_code == 401
    assert client.get("/dashboard").status_code == 401


def test_rnf04_motorista_nao_cadastra_nem_ve_roteiro_alheio(client, admin, motorista):
    outro = client.post(
        "/motoristas",
        headers=admin,
        json={
            "nome": "João Pereira",
            "telefone": "(31) 99999-0002",
            "documento": "987.654.321-00",
            "veiculo": "Fiorino",
            "rendimento_km_l": 10.5,
        },
    ).json()

    client.post(
        "/usuarios",
        headers=admin,
        json={
            "nome": "Carlos",
            "email": "carlos@teste.com",
            "senha": "carlos123",
            "perfil": "motorista",
            "motorista_id": motorista["id"],
        },
    )
    token = client.post(
        "/auth/login", json={"email": "carlos@teste.com", "senha": "carlos123"}
    ).json()["access_token"]
    cabecalho = {"Authorization": f"Bearer {token}"}

    # Motorista não pode cadastrar motorista nem alterar parâmetros.
    assert (
        client.post(
            "/motoristas",
            headers=cabecalho,
            json={
                "nome": "X",
                "telefone": "31999990000",
                "documento": "000",
                "veiculo": "Y",
                "rendimento_km_l": 10,
            },
        ).status_code
        == 403
    )
    assert client.put("/parametros", headers=cabecalho, json={"jornada_horas": 10}).status_code == 403

    # Nem enxergar o roteiro de outro motorista.
    alheio = client.post(
        "/roteiros",
        headers=admin,
        json={
            "data": "2026-03-12",
            "motorista_id": outro["id"],
            "distancia_total_km": 10,
            "pontos": [{"endereco": "Partida"}, {"endereco": "Cliente"}],
        },
    ).json()
    assert client.get(f"/roteiros/{alheio['id']}", headers=cabecalho).status_code == 403

    # Mas registra ponto no roteiro dele normalmente (RF05).
    proprio = client.post(
        "/roteiros",
        headers=admin,
        json={
            "data": "2026-03-12",
            "motorista_id": motorista["id"],
            "distancia_total_km": 10,
            "pontos": [{"endereco": "Partida"}, {"endereco": "Cliente"}],
        },
    ).json()
    assert (
        client.post(
            f"/roteiros/{proprio['id']}/pontos/1/chegada", headers=cabecalho, json={}
        ).status_code
        == 200
    )
    # A listagem do motorista só traz os roteiros dele.
    meus = client.get("/roteiros", headers=cabecalho).json()
    assert {r["motorista_id"] for r in meus} == {motorista["id"]}


def test_rnf05_auditoria_de_alteracoes_em_pontos_e_horarios(client, admin, roteiro):
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:05:00")

    eventos = client.get(
        "/auditoria", headers=admin, params={"entidade": "roteiro", "entidade_id": roteiro["id"]}
    ).json()
    acoes = {e["acao"] for e in eventos}
    assert {"criar", "registrar_chegada", "registrar_saida"} <= acoes
    assert all(e["usuario_email"] == "admin@teste.com" for e in eventos)


def test_rnf06_senha_nunca_volta_na_api(client, admin):
    criado = client.post(
        "/usuarios",
        headers=admin,
        json={
            "nome": "Teste LGPD",
            "email": "lgpd@teste.com",
            "senha": "segredo123",
            "perfil": "gerente",
        },
    ).json()
    assert "senha" not in criado and "senha_hash" not in criado
    for usuario in client.get("/usuarios", headers=admin).json():
        assert "senha_hash" not in usuario


def test_rnf03_dashboard_de_12_meses_responde_em_menos_de_3s(client, admin, motorista):
    from datetime import date, timedelta

    hoje = date.today()
    for dias in range(0, 360, 6):  # 60 roteiros espalhados por 12 meses
        dia = hoje - timedelta(days=dias)
        novo = client.post(
            "/roteiros",
            headers=admin,
            json={
                "data": dia.isoformat(),
                "motorista_id": motorista["id"],
                "distancia_total_km": 40,
                "pontos": [
                    {"endereco": "Partida"},
                    {"endereco": "Cliente A"},
                    {"endereco": "Cliente B"},
                ],
            },
        ).json()
        base = f"{dia.isoformat()}T08"
        marcar(client, admin, novo["id"], 1, f"{base}:00:00", f"{base}:05:00")
        marcar(client, admin, novo["id"], 2, f"{base}:30:00", f"{base}:45:00")

    inicio = time.perf_counter()
    resposta = client.get(
        "/dashboard",
        headers=admin,
        params={
            "agrupamento": "mes",
            "inicio": (hoje - timedelta(days=365)).isoformat(),
            "fim": hoje.isoformat(),
        },
    )
    decorrido = time.perf_counter() - inicio
    assert resposta.status_code == 200
    assert resposta.json()["indicadores"]["total_roteiros"] == 60
    assert decorrido < 3.0, f"Dashboard levou {decorrido:.2f}s (limite RNF03: 3s)"


def test_carga_de_demonstracao(client, admin):
    """A carga reproduz os roteiros A, B e C do exemplo da especificação."""
    resumo = client.post(
        "/admin/seed", headers=admin, params={"dias_historico": 10}
    ).json()
    assert resumo["motoristas"] == 3
    assert resumo["roteiros"] > 3

    historico = client.get("/historico", headers=admin, params={"somente_concluidos": True}).json()
    assert historico["total_registros"] > 0
    assert all(i["endereco"] for i in historico["itens"])
