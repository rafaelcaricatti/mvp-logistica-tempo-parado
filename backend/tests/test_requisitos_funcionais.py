"""Cobertura dos requisitos funcionais RF01 a RF12."""

from tests.conftest import marcar


def test_rf01_cadastro_de_motorista(client, admin, motorista):
    assert motorista["nome"] == "Carlos Silva"
    assert motorista["rendimento_km_l"] == 35.0
    listagem = client.get("/motoristas", headers=admin).json()
    assert any(m["id"] == motorista["id"] for m in listagem)


def test_rf02_cadastro_de_gerente(client, admin):
    resposta = client.post(
        "/gerentes",
        headers=admin,
        json={
            "nome": "Ana Coordenadora",
            "telefone": "(31) 98888-1000",
            "email": "ana@parouai.com",
            "equipe": [],
        },
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["email"] == "ana@parouai.com"


def test_rf03_cadastro_de_ponto_com_coordenadas(client, admin):
    resposta = client.post(
        "/pontos",
        headers=admin,
        json={
            "apelido": "Cliente Peru",
            "endereco": "Rua Peru, 55 - Belo Horizonte/MG",
            "latitude": -19.9318,
            "longitude": -43.9401,
        },
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["latitude"] == -19.9318 and corpo["longitude"] == -43.9401


def test_rf04_monta_roteiro_a_partir_de_pontos_cadastrados(client, admin, motorista):
    ponto = client.post(
        "/pontos", headers=admin, json={"endereco": "Rua X, 5", "latitude": -19.9, "longitude": -44.0}
    ).json()
    resposta = client.post(
        "/roteiros",
        headers=admin,
        json={
            "data": "2026-03-11",
            "motorista_id": motorista["id"],
            "distancia_total_km": 20,
            "pontos": [{"endereco": "Partida"}, {"ponto_id": ponto["id"]}],
        },
    )
    assert resposta.status_code == 201, resposta.text
    segundo = resposta.json()["pontos"][1]
    assert segundo["endereco"] == "Rua X, 5"
    assert segundo["latitude"] == -19.9


def test_rf05_registro_de_chegada_e_saida(client, admin, roteiro):
    atualizado = marcar(
        client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:04:00"
    )
    assert atualizado["pontos"][0]["chegada"].startswith("2026-03-10T08:00")
    assert atualizado["pontos"][0]["status"] == "concluida"


def test_rf06_calculo_automatico(client, admin, roteiro):
    atualizado = marcar(
        client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:05:00"
    )
    atualizado = marcar(
        client, admin, roteiro["id"], 2, "2026-03-10T08:20:00", "2026-03-10T08:32:00"
    )
    assert atualizado["pontos"][1]["tempo_parado_min"] == 12.0
    assert atualizado["tempo_total_parado_min"] == 12.0


def test_rf07_historico_traz_endereco_e_horarios(client, admin, roteiro):
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:05:00")
    marcar(client, admin, roteiro["id"], 2, "2026-03-10T08:20:00", "2026-03-10T08:35:00")

    resposta = client.get(
        "/historico", headers=admin, params={"inicio": "2026-03-01", "fim": "2026-03-31"}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["tempo_total_parado_min"] == 15.0
    item = next(i for i in corpo["itens"] if i["ordem"] == 2)
    # Critério de aceitação: tempo parado sempre ligado a endereço e data/hora.
    assert item["endereco"] == "Rua Peru, 55"
    assert item["chegada"] and item["saida"] and item["data"] == "2026-03-10"


def test_rf08_dashboard_nos_tres_recortes(client, admin, roteiro):
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:05:00")
    marcar(client, admin, roteiro["id"], 2, "2026-03-10T08:20:00", "2026-03-10T08:40:00")
    parametros = {"inicio": "2026-03-01", "fim": "2026-03-31"}

    por_dia = client.get(
        "/dashboard", headers=admin, params={**parametros, "agrupamento": "dia"}
    ).json()
    assert por_dia["serie"][0]["rotulo"] == "2026-03-10"
    assert por_dia["serie"][0]["tempo_parado_min"] == 20.0

    por_mes = client.get(
        "/dashboard", headers=admin, params={**parametros, "agrupamento": "mes"}
    ).json()
    assert por_mes["serie"][0]["rotulo"] == "2026-03"

    por_periodo = client.get(
        "/dashboard", headers=admin, params={**parametros, "agrupamento": "periodo"}
    ).json()
    assert por_periodo["serie"][0]["rotulo"] == "2026-03-01 a 2026-03-31"
    assert por_periodo["indicadores"]["jornada_horas"] == 8.0
    assert por_periodo["ranking_enderecos"][0]["rotulo"] == "Rua Peru, 55"


def test_rf09_rf10_parametros_alteraveis_sem_mexer_no_codigo(client, admin, motorista):
    resposta = client.put(
        "/parametros",
        headers=admin,
        json={
            "valor_combustivel": 7.00,
            "custo_por_km": 2.00,
            "jornada_horas": 6.0,
            "tolerancia_minutos": 5.0,
            "arredondamento_minutos": 5,
        },
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["jornada_horas"] == 6.0

    roteiro = client.post(
        "/roteiros",
        headers=admin,
        json={
            "data": "2026-04-01",
            "motorista_id": motorista["id"],
            "distancia_total_km": 35.0,
            "pontos": [{"endereco": "Partida"}, {"endereco": "Cliente"}],
        },
    ).json()
    # Novo preço do combustível e novo custo por km entram no cálculo na hora.
    assert roteiro["custo_detalhado"]["valor_combustivel"] == 7.00
    assert roteiro["custo_estimado"] == 77.0

    # Tolerância de 5 min: parada de 3 min é desprezada.
    atualizado = marcar(
        client, admin, roteiro["id"], 1, "2026-04-01T08:00:00", "2026-04-01T08:02:00"
    )
    atualizado = marcar(
        client, admin, roteiro["id"], 2, "2026-04-01T08:30:00", "2026-04-01T08:33:00"
    )
    assert atualizado["pontos"][1]["tempo_parado_min"] == 0.0


def test_rf10_arredondamento_configuravel(client, admin, motorista):
    client.put("/parametros", headers=admin, json={"arredondamento_minutos": 15})
    roteiro = client.post(
        "/roteiros",
        headers=admin,
        json={
            "data": "2026-04-02",
            "motorista_id": motorista["id"],
            "distancia_total_km": 10,
            "pontos": [{"endereco": "Partida"}, {"endereco": "Cliente"}],
        },
    ).json()
    marcar(client, admin, roteiro["id"], 1, "2026-04-02T08:00:00", "2026-04-02T08:01:00")
    atualizado = marcar(
        client, admin, roteiro["id"], 2, "2026-04-02T09:00:00", "2026-04-02T09:20:00"
    )
    assert atualizado["pontos"][1]["tempo_parado_min"] == 15.0


def test_rf12_exportacao_csv_e_relatorio(client, admin, roteiro):
    marcar(client, admin, roteiro["id"], 1, "2026-03-10T08:00:00", "2026-03-10T08:05:00")
    marcar(client, admin, roteiro["id"], 2, "2026-03-10T08:20:00", "2026-03-10T08:35:00")

    csv = client.get(
        "/relatorios/historico.csv",
        headers=admin,
        params={"inicio": "2026-03-01", "fim": "2026-03-31"},
    )
    assert csv.status_code == 200
    assert "endereco" in csv.text and "Rua Peru, 55" in csv.text
    assert "attachment" in csv.headers["content-disposition"]

    completo = client.get(
        "/relatorios/completo",
        headers=admin,
        params={"inicio": "2026-03-01", "fim": "2026-03-31"},
    ).json()
    assert completo["indicadores"]["tempo_total_parado_min"] == 15.0
    assert len(completo["historico"]) == 4
