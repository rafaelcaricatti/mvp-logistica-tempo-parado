"""Configuração dos testes: roda a API inteira contra o store em memória."""

import os
import sys
from pathlib import Path

os.environ["FIRESTORE_BACKEND"] = "memory"
os.environ["SECRET_KEY"] = "chave-de-teste"
os.environ["ADMIN_EMAIL"] = "admin@teste.com"
os.environ["ADMIN_SENHA"] = "admin123"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.core import firebase
from app.core.config import get_settings
from app.main import app


@pytest.fixture
def client():
    get_settings.cache_clear()
    firebase.resetar_store()
    with TestClient(app) as c:
        yield c
    firebase.resetar_store()


def _token(client, email, senha):
    resposta = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["access_token"]


@pytest.fixture
def admin(client):
    """Cabeçalho de autenticação do administrador criado no boot."""
    return {"Authorization": f"Bearer {_token(client, 'admin@teste.com', 'admin123')}"}


@pytest.fixture
def motorista(client, admin):
    """Cria um motorista e devolve o registro."""
    resposta = client.post(
        "/motoristas",
        headers=admin,
        json={
            "nome": "Carlos Silva",
            "telefone": "(31) 99999-0001",
            "documento": "123.456.789-00",
            "veiculo": "Moto Honda CG 160",
            "rendimento_km_l": 35.0,
        },
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture
def roteiro(client, admin, motorista):
    """Roteiro com 4 pontos, igual ao exemplo A da especificação."""
    resposta = client.post(
        "/roteiros",
        headers=admin,
        json={
            "data": "2026-03-10",
            "motorista_id": motorista["id"],
            "distancia_total_km": 45.5,
            "pontos": [
                {"endereco": "Seg. Família (partida)"},
                {"endereco": "Rua Peru, 55"},
                {"endereco": "Rua X, 5"},
                {"endereco": "Av. João César"},
            ],
        },
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def marcar(client, headers, roteiro_id, ordem, chegada, saida):
    """Registra chegada e saída em um ponto (RF05)."""
    r1 = client.post(
        f"/roteiros/{roteiro_id}/pontos/{ordem}/chegada",
        headers=headers,
        json={"horario": chegada},
    )
    assert r1.status_code == 200, r1.text
    r2 = client.post(
        f"/roteiros/{roteiro_id}/pontos/{ordem}/saida",
        headers=headers,
        json={"horario": saida},
    )
    assert r2.status_code == 200, r2.text
    return r2.json()
