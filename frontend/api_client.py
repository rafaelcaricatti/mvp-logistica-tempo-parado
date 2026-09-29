"""Cliente HTTP do front-end para a API do back-end.

Toda leitura e escrita da tela passa por aqui — a interface não conhece o
Firestore, só a API REST.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 20


class ApiError(RuntimeError):
    """Erro devolvido pela API, já com a mensagem pronta para a tela."""

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status


def _extrair_erro(resposta: requests.Response) -> str:
    try:
        corpo = resposta.json()
    except ValueError:
        return resposta.text or f"Erro HTTP {resposta.status_code}"
    detalhe = corpo.get("detail", corpo)
    if isinstance(detalhe, list):  # erros de validação do Pydantic
        return "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', [])[1:])}: {e.get('msg')}" for e in detalhe
        )
    return str(detalhe)


def _serializar(valor: Any) -> Any:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: _serializar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_serializar(v) for v in valor]
    return valor


class ApiClient:
    def __init__(self, base_url: str = BASE_URL, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    # -- infraestrutura ----------------------------------------------------
    def _cabecalhos(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _requisicao(self, metodo: str, caminho: str, **kwargs) -> Any:
        if "json" in kwargs and kwargs["json"] is not None:
            kwargs["json"] = _serializar(kwargs["json"])
        if "params" in kwargs and kwargs["params"]:
            kwargs["params"] = {
                k: _serializar(v) for k, v in kwargs["params"].items() if v is not None
            }
        try:
            resposta = requests.request(
                metodo,
                f"{self.base_url}{caminho}",
                headers=self._cabecalhos(),
                timeout=TIMEOUT,
                **kwargs,
            )
        except requests.RequestException as erro:
            raise ApiError(
                f"Não foi possível falar com a API em {self.base_url}. "
                f"Confira se o back-end está rodando. Detalhe: {erro}"
            ) from erro

        if resposta.status_code >= 400:
            raise ApiError(_extrair_erro(resposta), resposta.status_code)
        if resposta.status_code == 204 or not resposta.content:
            return None
        if resposta.headers.get("content-type", "").startswith("text/csv"):
            return resposta.text
        return resposta.json()

    # -- autenticação ------------------------------------------------------
    def login(self, email: str, senha: str) -> dict:
        dados = self._requisicao("POST", "/auth/login", json={"email": email, "senha": senha})
        self.token = dados["access_token"]
        return dados

    def saude(self) -> dict:
        return self._requisicao("GET", "/health")

    # -- RF01 motoristas ---------------------------------------------------
    def listar_motoristas(self) -> list[dict]:
        return self._requisicao("GET", "/motoristas")

    def criar_motorista(self, dados: dict) -> dict:
        return self._requisicao("POST", "/motoristas", json=dados)

    def atualizar_motorista(self, motorista_id: str, dados: dict) -> dict:
        return self._requisicao("PUT", f"/motoristas/{motorista_id}", json=dados)

    def remover_motorista(self, motorista_id: str) -> None:
        self._requisicao("DELETE", f"/motoristas/{motorista_id}")

    # -- RF02 gerentes -----------------------------------------------------
    def listar_gerentes(self) -> list[dict]:
        return self._requisicao("GET", "/gerentes")

    def criar_gerente(self, dados: dict) -> dict:
        return self._requisicao("POST", "/gerentes", json=dados)

    def remover_gerente(self, gerente_id: str) -> None:
        self._requisicao("DELETE", f"/gerentes/{gerente_id}")

    # -- RF03 pontos -------------------------------------------------------
    def listar_pontos(self) -> list[dict]:
        return self._requisicao("GET", "/pontos")

    def criar_ponto(self, dados: dict) -> dict:
        return self._requisicao("POST", "/pontos", json=dados)

    def remover_ponto(self, ponto_id: str) -> None:
        self._requisicao("DELETE", f"/pontos/{ponto_id}")

    # -- RF04/RF05 roteiros ------------------------------------------------
    def listar_roteiros(
        self, inicio: date | None = None, fim: date | None = None, motorista_id: str | None = None
    ) -> list[dict]:
        return self._requisicao(
            "GET",
            "/roteiros",
            params={"inicio": inicio, "fim": fim, "motorista_id": motorista_id},
        )

    def obter_roteiro(self, roteiro_id: str) -> dict:
        return self._requisicao("GET", f"/roteiros/{roteiro_id}")

    def criar_roteiro(self, dados: dict) -> dict:
        return self._requisicao("POST", "/roteiros", json=dados)

    def remover_roteiro(self, roteiro_id: str) -> None:
        self._requisicao("DELETE", f"/roteiros/{roteiro_id}")

    def registrar_chegada(self, roteiro_id: str, ordem: int, horario=None) -> dict:
        return self._requisicao(
            "POST", f"/roteiros/{roteiro_id}/pontos/{ordem}/chegada", json={"horario": horario}
        )

    def registrar_saida(self, roteiro_id: str, ordem: int, horario=None) -> dict:
        return self._requisicao(
            "POST", f"/roteiros/{roteiro_id}/pontos/{ordem}/saida", json={"horario": horario}
        )

    # -- RF07/RF08 histórico e dashboard -----------------------------------
    def historico(
        self,
        inicio: date | None = None,
        fim: date | None = None,
        motorista_id: str | None = None,
        somente_concluidos: bool = False,
    ) -> dict:
        return self._requisicao(
            "GET",
            "/historico",
            params={
                "inicio": inicio,
                "fim": fim,
                "motorista_id": motorista_id,
                "somente_concluidos": somente_concluidos,
            },
        )

    def dashboard(
        self,
        agrupamento: str = "dia",
        inicio: date | None = None,
        fim: date | None = None,
        motorista_id: str | None = None,
    ) -> dict:
        return self._requisicao(
            "GET",
            "/dashboard",
            params={
                "agrupamento": agrupamento,
                "inicio": inicio,
                "fim": fim,
                "motorista_id": motorista_id,
            },
        )

    # -- RF09/RF10 parâmetros ---------------------------------------------
    def obter_parametros(self) -> dict:
        return self._requisicao("GET", "/parametros")

    def atualizar_parametros(self, dados: dict) -> dict:
        return self._requisicao("PUT", "/parametros", json=dados)

    # -- RF12 relatórios ---------------------------------------------------
    def exportar_csv(
        self, inicio: date | None, fim: date | None, motorista_id: str | None = None
    ) -> str:
        return self._requisicao(
            "GET",
            "/relatorios/historico.csv",
            params={"inicio": inicio, "fim": fim, "motorista_id": motorista_id},
        )

    def relatorio_completo(
        self, inicio: date | None, fim: date | None, motorista_id: str | None = None
    ) -> dict:
        return self._requisicao(
            "GET",
            "/relatorios/completo",
            params={"inicio": inicio, "fim": fim, "motorista_id": motorista_id},
        )

    # -- RNF04/RNF05 usuários e auditoria ----------------------------------
    def listar_usuarios(self) -> list[dict]:
        return self._requisicao("GET", "/usuarios")

    def criar_usuario(self, dados: dict) -> dict:
        return self._requisicao("POST", "/usuarios", json=dados)

    def remover_usuario(self, usuario_id: str) -> None:
        self._requisicao("DELETE", f"/usuarios/{usuario_id}")

    def auditoria(self, entidade: str | None = None, limite: int = 200) -> list[dict]:
        return self._requisicao(
            "GET", "/auditoria", params={"entidade": entidade, "limite": limite}
        )

    def seed(self, dias_historico: int = 120) -> dict:
        return self._requisicao(
            "POST", "/admin/seed", params={"dias_historico": dias_historico}
        )
