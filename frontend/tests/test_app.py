"""Smoke test do front-end: sobe a API de verdade e percorre todas as telas.

Garante que a interface continua conversando com o contrato da API — nenhuma
tela usa dados mockados.
"""

from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest

ADMIN_EMAIL = "admin@parouai.com"
ADMIN_SENHA = "admin123"

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "frontend" / "app.py"


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api_em_execucao():
    """Sobe a API em uma thread, com persistência em memória, e popula a base."""
    import sys

    sys.path.insert(0, str(RAIZ / "backend"))

    # Ambiente próprio: não depende de quem rodou antes na mesma sessão.
    os.environ["FIRESTORE_BACKEND"] = "memory"
    os.environ["SECRET_KEY"] = "chave-de-teste-front"
    os.environ["ADMIN_EMAIL"] = ADMIN_EMAIL
    os.environ["ADMIN_SENHA"] = ADMIN_SENHA

    import uvicorn

    from app.core import firebase
    from app.core.config import get_settings

    get_settings.cache_clear()
    firebase.resetar_store()

    from app.main import app as fastapi_app

    porta = _porta_livre()
    config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=porta, log_level="warning")
    servidor = uvicorn.Server(config)
    thread = threading.Thread(target=servidor.run, daemon=True)
    thread.start()

    limite = time.time() + 30
    while not servidor.started and time.time() < limite:
        time.sleep(0.1)
    assert servidor.started, "A API de teste não subiu."

    base = f"http://127.0.0.1:{porta}"
    os.environ["API_BASE_URL"] = base

    from frontend.api_client import ApiClient

    cliente = ApiClient(base)
    cliente.login(ADMIN_EMAIL, ADMIN_SENHA)
    cliente.seed(dias_historico=15)

    yield base

    servidor.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def app_autenticado(api_em_execucao):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=90).run()
    assert not at.exception, at.exception
    at.text_input[0].set_value(ADMIN_EMAIL)
    at.text_input[1].set_value(ADMIN_SENHA)
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


def test_login_exigido_antes_de_qualquer_tela(api_em_execucao):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=90).run()
    assert not at.exception
    assert not at.radio, "A navegação não pode aparecer sem autenticação (RNF04)."


def test_gestao_ve_todas_as_telas_sem_erro(app_autenticado):
    at = app_autenticado
    paginas = at.radio[0].options
    assert paginas == [
        "Dashboard",
        "Registro de Ponto",
        "Histórico",
        "Cadastros",
        "Configurações",
        "Administração",
    ]
    for pagina in paginas:
        at.radio[0].set_value(pagina).run()
        assert not at.exception, f"{pagina}: {at.exception}"
        assert not [e.value for e in at.error], f"{pagina}: {[e.value for e in at.error]}"


def test_dashboard_mostra_grafico_e_indicadores(app_autenticado):
    at = app_autenticado
    at.radio[0].set_value("Dashboard").run()
    assert at.get("plotly_chart"), "O dashboard precisa renderizar o gráfico (RF08)."
    rotulos = [m.label for m in at.metric]
    assert "Tempo total parado" in rotulos
    assert any("Jornadas de" in r for r in rotulos)  # RN04


def test_motorista_so_enxerga_as_proprias_telas(api_em_execucao):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=90).run()
    at.text_input[0].set_value("motorista@parouai.com")
    at.text_input[1].set_value("motorista123")
    at.button[0].click().run()
    assert not at.exception, at.exception
    # RNF04 — sem Cadastros, Configurações nem Administração.
    assert at.radio[0].options == ["Dashboard", "Registro de Ponto", "Histórico"]
