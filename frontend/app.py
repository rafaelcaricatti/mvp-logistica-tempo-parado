"""Front-end Streamlit do MVP de Monitoramento de Tempo Parado.

Interface web responsiva (RNF02) que consome exclusivamente a API REST do
back-end — nenhum dado é mantido em mock.

Execute com:  streamlit run frontend/app.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# No Streamlit Community Cloud a URL da API vem de st.secrets (Settings → Secrets),
# não de variável de ambiente. Localmente, API_BASE_URL no shell continua valendo.
try:
    if "API_BASE_URL" in st.secrets:
        os.environ["API_BASE_URL"] = st.secrets["API_BASE_URL"]
except Exception:
    pass  # sem secrets.toml (uso local) — segue com o valor padrão/variável de ambiente

from frontend.api_client import BASE_URL, ApiClient, ApiError  # noqa: E402

st.set_page_config(
    page_title="ParouAí · Monitoramento de Tempo Parado",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PERFIS_GESTAO = {"gerente", "administrador"}


# ---------------------------------------------------------------------------
# Sessão
# ---------------------------------------------------------------------------
def api() -> ApiClient:
    if "api" not in st.session_state:
        st.session_state.api = ApiClient(token=st.session_state.get("token"))
    st.session_state.api.token = st.session_state.get("token")
    return st.session_state.api


def usuario() -> dict:
    return st.session_state.get("usuario") or {}


def e_gestao() -> bool:
    return usuario().get("perfil") in PERFIS_GESTAO


def erro(mensagem: ApiError | str) -> None:
    st.error(str(mensagem))


# ---------------------------------------------------------------------------
# Login (RNF04)
# ---------------------------------------------------------------------------
def tela_login() -> None:
    esquerda, centro, direita = st.columns([1, 2, 1])
    with centro:
        st.title("⏱️ ParouAí")
        st.caption("Sistema de Monitoramento de Tempo Parado em Roteiros")
        st.divider()

        with st.form("login"):
            email = st.text_input("E-mail", value="admin@parouai.com")
            senha = st.text_input("Senha", type="password", value="admin123")
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")

        if entrar:
            try:
                dados = ApiClient().login(email, senha)
            except ApiError as falha:
                erro(falha)
                return
            st.session_state.token = dados["access_token"]
            st.session_state.usuario = dados["usuario"]
            st.rerun()

        with st.expander("Credenciais de demonstração"):
            st.markdown(
                """
                | Perfil | E-mail | Senha |
                |---|---|---|
                | Administrador | `admin@parouai.com` | `admin123` |
                | Gerente | `gerente@parouai.com` | `gerente123` |
                | Motorista | `motorista@parouai.com` | `motorista123` |

                Os dois últimos são criados pela carga de demonstração
                (`python backend/seed.py` ou o botão em *Administração*).
                """
            )
        st.caption(f"API configurada em `{BASE_URL}`")


# ---------------------------------------------------------------------------
# Auxiliares de tela
# ---------------------------------------------------------------------------
def seletor_periodo(chave: str, dias_padrao: int = 30) -> tuple[date, date]:
    hoje = date.today()
    coluna1, coluna2 = st.columns(2)
    inicio = coluna1.date_input(
        "Data inicial", value=hoje - timedelta(days=dias_padrao), key=f"{chave}_inicio",
        format="DD/MM/YYYY",
    )
    fim = coluna2.date_input("Data final", value=hoje, key=f"{chave}_fim", format="DD/MM/YYYY")
    return inicio, fim


def seletor_motorista(chave: str, motoristas: list[dict]) -> str | None:
    if not e_gestao():
        return None
    opcoes = {"Todos": None} | {m["nome"]: m["id"] for m in motoristas}
    escolha = st.selectbox("Motorista", list(opcoes), key=f"{chave}_motorista")
    return opcoes[escolha]


def formatar_minutos(minutos: float) -> str:
    horas, resto = divmod(int(round(minutos)), 60)
    return f"{horas}h {resto:02d}min" if horas else f"{resto} min"


def hora_curta(iso: str | None) -> str:
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).strftime("%H:%M:%S")


@st.cache_data(ttl=30, show_spinner=False)
def carregar_motoristas(_token: str) -> list[dict]:
    return api().listar_motoristas()


# ---------------------------------------------------------------------------
# RF08 — Dashboard
# ---------------------------------------------------------------------------
def pagina_dashboard() -> None:
    st.title("Dashboard Gerencial")
    st.caption("Tempo parado por dia, por mês e por período — RF08")

    motoristas = carregar_motoristas(st.session_state.token)

    with st.container(border=True):
        coluna1, coluna2 = st.columns([1, 2])
        with coluna1:
            rotulos = {"Por dia": "dia", "Por mês": "mes", "Por período": "periodo"}
            visao = st.selectbox("Recorte de visualização", list(rotulos))
            agrupamento = rotulos[visao]
        with coluna2:
            motorista_id = seletor_motorista("dash", motoristas)
        inicio, fim = seletor_periodo("dash", 90 if agrupamento == "mes" else 30)

    try:
        dados = api().dashboard(agrupamento, inicio, fim, motorista_id)
    except ApiError as falha:
        erro(falha)
        return

    indicadores = dados["indicadores"]
    serie = pd.DataFrame(dados["serie"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tempo total parado", formatar_minutos(indicadores["tempo_total_parado_min"]))
    c2.metric(
        f"Jornadas de {indicadores['jornada_horas']:g}h consumidas",
        f"{indicadores['jornadas_equivalentes']:.2f}",
        help="RN04 — tempo parado dividido pela jornada padrão configurada.",
    )
    c3.metric("Custo estimado do período", f"R$ {indicadores['custo_total_estimado']:,.2f}")
    c4.metric("Média por parada", formatar_minutos(indicadores["tempo_medio_por_parada_min"]))

    if serie.empty:
        st.info("Nenhum roteiro encontrado no período selecionado.")
        return

    if agrupamento == "dia":
        figura = px.line(
            serie, x="rotulo", y="tempo_parado_min", markers=True,
            title="Tempo parado por dia (min)",
            labels={"rotulo": "Dia", "tempo_parado_min": "Minutos parados"},
        )
    else:
        titulo = "Tempo parado por mês (min)" if agrupamento == "mes" else "Tempo parado no período (min)"
        eixo = "Mês" if agrupamento == "mes" else "Período"
        figura = px.bar(
            serie, x="rotulo", y="tempo_parado_min", text_auto=".0f", title=titulo,
            labels={"rotulo": eixo, "tempo_parado_min": "Minutos parados"},
        )
    figura.update_layout(margin=dict(l=0, r=0, t=50, b=0), plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(figura, width="stretch")

    coluna1, coluna2 = st.columns(2)
    with coluna1:
        st.subheader("Onde mais se perde tempo")
        enderecos = pd.DataFrame(dados["ranking_enderecos"])
        if enderecos.empty:
            st.caption("Sem paradas registradas no período.")
        else:
            grafico = px.bar(
                enderecos.sort_values("tempo_parado_min"),
                x="tempo_parado_min", y="rotulo", orientation="h",
                labels={"tempo_parado_min": "Minutos parados", "rotulo": "Endereço"},
            )
            grafico.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
            st.plotly_chart(grafico, width="stretch")
    with coluna2:
        st.subheader("Tempo parado por motorista")
        por_motorista = pd.DataFrame(dados["ranking_motoristas"])
        if por_motorista.empty:
            st.caption("Sem roteiros no período.")
        else:
            st.dataframe(
                por_motorista.rename(
                    columns={
                        "rotulo": "Motorista",
                        "tempo_parado_min": "Minutos parados",
                        "ocorrencias": "Roteiros",
                    }
                )[["Motorista", "Minutos parados", "Roteiros"]],
                width="stretch", hide_index=True,
            )

    with st.expander("Detalhamento da série"):
        st.dataframe(
            serie.rename(
                columns={
                    "rotulo": "Período",
                    "tempo_parado_min": "Minutos parados",
                    "distancia_km": "Distância (km)",
                    "roteiros": "Roteiros",
                    "paradas": "Paradas",
                    "custo_estimado": "Custo (R$)",
                }
            ),
            width="stretch", hide_index=True,
        )


# ---------------------------------------------------------------------------
# RF05 — App do motorista
# ---------------------------------------------------------------------------
def pagina_motorista() -> None:
    st.title("Registro de Ponto")
    st.caption("Coleta de chegada e saída em cada ponto do roteiro — RF05")

    hoje = date.today()
    motorista_id = usuario().get("motorista_id")

    if e_gestao():
        motoristas = carregar_motoristas(st.session_state.token)
        if not motoristas:
            st.info("Cadastre um motorista antes de registrar pontos.")
            return
        nomes = {m["nome"]: m["id"] for m in motoristas}
        motorista_id = nomes[st.selectbox("Motorista", list(nomes))]

    data_roteiro = st.date_input("Data do roteiro", value=hoje, format="DD/MM/YYYY")

    try:
        roteiros = api().listar_roteiros(data_roteiro, data_roteiro, motorista_id)
    except ApiError as falha:
        erro(falha)
        return

    if not roteiros:
        st.info("Nenhum roteiro atribuído para este motorista nesta data.")
        return

    rotulos = {
        f"{r['id'][:6]} · {len(r['pontos'])} pontos · {r['status'].replace('_', ' ')}": r
        for r in roteiros
    }
    roteiro = rotulos[st.selectbox("Roteiro", list(rotulos))] if len(rotulos) > 1 else roteiros[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Distância prevista", f"{roteiro['distancia_total_km']:g} km")
    c2.metric("Tempo parado até agora", formatar_minutos(roteiro["tempo_total_parado_min"]))
    c3.metric("Custo estimado", f"R$ {roteiro['custo_estimado']:,.2f}")

    st.divider()

    pontos = roteiro["pontos"]
    proximo = next((p for p in pontos if p["status"] != "concluida"), None)

    if proximo is None:
        st.success("Todos os pontos do roteiro foram concluídos.")
    else:
        with st.container(border=True):
            marca = " (ponto de partida — não conta tempo parado)" if proximo["ordem"] == 1 else ""
            st.subheader(f"Ponto {proximo['ordem']}: {proximo['endereco']}{marca}")

            coluna1, coluna2 = st.columns(2)
            with coluna1:
                if proximo["chegada"] is None:
                    if st.button("📍 Registrar chegada", type="primary", width="stretch"):
                        try:
                            api().registrar_chegada(roteiro["id"], proximo["ordem"])
                            st.rerun()
                        except ApiError as falha:
                            erro(falha)
                else:
                    st.metric("Chegada", hora_curta(proximo["chegada"]))
            with coluna2:
                if proximo["chegada"] is not None:
                    if st.button("🚚 Registrar saída", type="primary", width="stretch"):
                        try:
                            api().registrar_saida(roteiro["id"], proximo["ordem"])
                            st.rerun()
                        except ApiError as falha:
                            erro(falha)
                else:
                    st.caption("Registre a chegada primeiro.")

    st.subheader("Pontos do roteiro")
    tabela = pd.DataFrame(
        [
            {
                "Ordem": p["ordem"],
                "Endereço": p["endereco"],
                "Chegada": hora_curta(p["chegada"]),
                "Saída": hora_curta(p["saida"]),
                "Tempo parado": (
                    "—" if p["tempo_parado_min"] is None
                    else ("não conta" if p["ordem"] == 1 else formatar_minutos(p["tempo_parado_min"]))
                ),
                "Status": p["status"].replace("_", " ").capitalize(),
            }
            for p in pontos
        ]
    )
    st.dataframe(tabela, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# RF07 / RF12 — Histórico e exportação
# ---------------------------------------------------------------------------
def pagina_historico() -> None:
    st.title("Histórico de Paradas")
    st.caption("Pontos e tempos parados por período, com endereços — RF07")

    motoristas = carregar_motoristas(st.session_state.token) if e_gestao() else []
    with st.container(border=True):
        inicio, fim = seletor_periodo("hist", 30)
        coluna1, coluna2 = st.columns(2)
        with coluna1:
            motorista_id = seletor_motorista("hist", motoristas)
        with coluna2:
            somente_concluidos = st.checkbox("Somente paradas concluídas", value=False)

    try:
        dados = api().historico(inicio, fim, motorista_id, somente_concluidos)
    except ApiError as falha:
        erro(falha)
        return

    c1, c2 = st.columns(2)
    c1.metric("Registros no período", dados["total_registros"])
    c2.metric("Tempo total parado", formatar_minutos(dados["tempo_total_parado_min"]))

    if not dados["itens"]:
        st.info("Nenhum registro no período selecionado.")
        return

    tabela = pd.DataFrame(
        [
            {
                "Data": datetime.fromisoformat(i["data"]).strftime("%d/%m/%Y"),
                "Motorista": i["motorista_nome"],
                "Ordem": i["ordem"],
                "Endereço": i["endereco"],
                "Chegada": hora_curta(i["chegada"]),
                "Saída": hora_curta(i["saida"]),
                "Tempo parado (min)": 0 if i["ponto_de_partida"] else i["tempo_parado_min"],
                "Partida": "sim" if i["ponto_de_partida"] else "não",
            }
            for i in dados["itens"]
        ]
    )
    st.dataframe(tabela, width="stretch", hide_index=True)

    # RF12 — exportação do período consultado.
    try:
        csv = api().exportar_csv(inicio, fim, motorista_id)
        st.download_button(
            "⬇️ Exportar relatório do período (CSV)",
            data=csv.encode("utf-8-sig"),
            file_name=f"historico_{inicio}_{fim}.csv",
            mime="text/csv",
            type="primary",
        )
    except ApiError as falha:
        erro(falha)


# ---------------------------------------------------------------------------
# RF01 / RF02 / RF03 / RF04 — Cadastros
# ---------------------------------------------------------------------------
def pagina_cadastros() -> None:
    st.title("Cadastros")
    st.caption("Motoristas, gerentes, pontos e montagem dos roteiros — RF01 a RF04")

    aba_motoristas, aba_gerentes, aba_pontos, aba_roteiros = st.tabs(
        ["Motoristas (RF01)", "Gerentes (RF02)", "Pontos (RF03)", "Roteiros (RF04)"]
    )

    with aba_motoristas:
        _aba_motoristas()
    with aba_gerentes:
        _aba_gerentes()
    with aba_pontos:
        _aba_pontos()
    with aba_roteiros:
        _aba_roteiros()


def _aba_motoristas() -> None:
    with st.form("form_motorista", clear_on_submit=True):
        coluna1, coluna2 = st.columns(2)
        nome = coluna1.text_input("Nome completo")
        documento = coluna1.text_input("Documento (CPF/CNH)")
        telefone = coluna2.text_input("Telefone")
        veiculo = coluna2.text_input("Veículo")
        rendimento = st.number_input(
            "Rendimento do veículo (km/litro)", min_value=0.1, value=12.0, step=0.5
        )
        if st.form_submit_button("Salvar motorista", type="primary"):
            try:
                api().criar_motorista(
                    {
                        "nome": nome,
                        "telefone": telefone,
                        "documento": documento,
                        "veiculo": veiculo,
                        "rendimento_km_l": rendimento,
                    }
                )
                st.cache_data.clear()
                st.success("Motorista cadastrado.")
            except ApiError as falha:
                erro(falha)

    try:
        motoristas = api().listar_motoristas()
    except ApiError as falha:
        erro(falha)
        return
    if motoristas:
        st.dataframe(
            pd.DataFrame(motoristas)[
                ["nome", "telefone", "documento", "veiculo", "rendimento_km_l"]
            ].rename(
                columns={
                    "nome": "Nome", "telefone": "Telefone", "documento": "Documento",
                    "veiculo": "Veículo", "rendimento_km_l": "km/litro",
                }
            ),
            width="stretch", hide_index=True,
        )
        remover = st.selectbox(
            "Remover motorista", ["—"] + [f"{m['nome']} ({m['id'][:6]})" for m in motoristas]
        )
        if remover != "—" and st.button("Remover", key="rm_motorista"):
            identificador = remover.split("(")[-1].rstrip(")")
            alvo = next(m for m in motoristas if m["id"].startswith(identificador))
            try:
                api().remover_motorista(alvo["id"])
                st.cache_data.clear()
                st.rerun()
            except ApiError as falha:
                erro(falha)


def _aba_gerentes() -> None:
    try:
        motoristas = api().listar_motoristas()
    except ApiError as falha:
        erro(falha)
        return

    with st.form("form_gerente", clear_on_submit=True):
        coluna1, coluna2 = st.columns(2)
        nome = coluna1.text_input("Nome completo")
        email = coluna1.text_input("E-mail")
        telefone = coluna2.text_input("Telefone")
        equipe_nomes = st.multiselect(
            "Equipe sob responsabilidade", [m["nome"] for m in motoristas]
        )
        if st.form_submit_button("Salvar gerente", type="primary"):
            equipe = [m["id"] for m in motoristas if m["nome"] in equipe_nomes]
            try:
                api().criar_gerente(
                    {"nome": nome, "telefone": telefone, "email": email, "equipe": equipe}
                )
                st.success("Gerente cadastrado.")
            except ApiError as falha:
                erro(falha)

    try:
        gerentes = api().listar_gerentes()
    except ApiError as falha:
        erro(falha)
        return
    if gerentes:
        nomes = {m["id"]: m["nome"] for m in motoristas}
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Nome": g["nome"],
                        "Telefone": g["telefone"],
                        "E-mail": g["email"],
                        "Equipe": ", ".join(nomes.get(i, i) for i in g.get("equipe", [])) or "—",
                    }
                    for g in gerentes
                ]
            ),
            width="stretch", hide_index=True,
        )


def _aba_pontos() -> None:
    with st.form("form_ponto", clear_on_submit=True):
        apelido = st.text_input("Apelido (opcional)")
        endereco = st.text_input("Endereço completo")
        coluna1, coluna2 = st.columns(2)
        latitude = coluna1.number_input("Latitude", value=0.0, format="%.6f")
        longitude = coluna2.number_input("Longitude", value=0.0, format="%.6f")
        if st.form_submit_button("Salvar ponto", type="primary"):
            try:
                api().criar_ponto(
                    {
                        "apelido": apelido or None,
                        "endereco": endereco,
                        "latitude": latitude or None,
                        "longitude": longitude or None,
                    }
                )
                st.success("Ponto cadastrado.")
            except ApiError as falha:
                erro(falha)

    try:
        pontos = api().listar_pontos()
    except ApiError as falha:
        erro(falha)
        return
    if pontos:
        st.dataframe(
            pd.DataFrame(pontos)[["apelido", "endereco", "latitude", "longitude"]].rename(
                columns={
                    "apelido": "Apelido", "endereco": "Endereço",
                    "latitude": "Latitude", "longitude": "Longitude",
                }
            ),
            width="stretch", hide_index=True,
        )
        mapa = pd.DataFrame(
            [
                {"lat": p["latitude"], "lon": p["longitude"]}
                for p in pontos
                if p.get("latitude") and p.get("longitude")
            ]
        )
        if not mapa.empty:
            st.map(mapa, size=40)


def _aba_roteiros() -> None:
    try:
        motoristas = api().listar_motoristas()
        pontos = api().listar_pontos()
    except ApiError as falha:
        erro(falha)
        return

    if not motoristas:
        st.info("Cadastre pelo menos um motorista para montar roteiros.")
        return

    with st.form("form_roteiro"):
        coluna1, coluna2 = st.columns(2)
        data_roteiro = coluna1.date_input(
            "Data de execução", value=date.today(), format="DD/MM/YYYY"
        )
        nomes = {m["nome"]: m["id"] for m in motoristas}
        motorista_id = nomes[coluna2.selectbox("Motorista responsável", list(nomes))]
        distancia = st.number_input("Distância estimada do roteiro (km)", min_value=0.0, value=40.0)

        rotulos_pontos = {
            f"{p.get('apelido') or p['endereco']} — {p['endereco']}": p["id"] for p in pontos
        }
        escolhidos = st.multiselect(
            "Pontos cadastrados (a ordem de seleção define o trajeto)", list(rotulos_pontos)
        )
        avulsos = st.text_area(
            "Endereços avulsos (um por linha, entram depois dos pontos acima)",
            placeholder="Rua Seg. Família, 10 (partida)\nRua Peru, 55",
            height=100,
        )
        st.caption("O primeiro ponto do roteiro é a partida e não acumula tempo parado (RN01).")

        if st.form_submit_button("Gerar roteiro", type="primary"):
            lista = [{"ponto_id": rotulos_pontos[r]} for r in escolhidos]
            lista += [
                {"endereco": linha.strip()}
                for linha in avulsos.splitlines()
                if linha.strip()
            ]
            if len(lista) < 2:
                st.warning("Informe pelo menos dois pontos (partida + uma parada).")
            else:
                try:
                    criado = api().criar_roteiro(
                        {
                            "data": data_roteiro,
                            "motorista_id": motorista_id,
                            "distancia_total_km": distancia,
                            "pontos": lista,
                        }
                    )
                    st.success(
                        f"Roteiro criado com {len(criado['pontos'])} pontos · "
                        f"custo estimado R$ {criado['custo_estimado']:,.2f}"
                    )
                except ApiError as falha:
                    erro(falha)

    st.divider()
    st.subheader("Roteiros dos últimos 30 dias")
    try:
        roteiros = api().listar_roteiros(date.today() - timedelta(days=30), date.today())
    except ApiError as falha:
        erro(falha)
        return
    if not roteiros:
        st.caption("Nenhum roteiro no período.")
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Data": datetime.fromisoformat(r["data"]).strftime("%d/%m/%Y"),
                    "Motorista": r["motorista_nome"],
                    "Pontos": len(r["pontos"]),
                    "Distância (km)": r["distancia_total_km"],
                    "Tempo parado (min)": r["tempo_total_parado_min"],
                    "Custo (R$)": r["custo_estimado"],
                    "Status": r["status"].replace("_", " ").capitalize(),
                }
                for r in sorted(roteiros, key=lambda x: x["data"], reverse=True)
            ]
        ),
        width="stretch", hide_index=True,
    )


# ---------------------------------------------------------------------------
# RF09 / RF10 — Configurações
# ---------------------------------------------------------------------------
def pagina_configuracoes() -> None:
    st.title("Configurações")
    st.caption("Parâmetros de custo e de cálculo do tempo parado — RF09 e RF10")

    try:
        atuais = api().obter_parametros()
    except ApiError as falha:
        erro(falha)
        return

    with st.form("form_parametros"):
        st.subheader("Custos (RF09)")
        coluna1, coluna2, coluna3 = st.columns(3)
        valor_combustivel = coluna1.number_input(
            "Valor do combustível (R$/litro)", value=float(atuais["valor_combustivel"]), step=0.10
        )
        custo_por_km = coluna2.number_input(
            "Custo operacional por km (R$)", value=float(atuais["custo_por_km"]), step=0.10
        )
        rendimento_padrao = coluna3.number_input(
            "Rendimento padrão (km/litro)", value=float(atuais["rendimento_km_l_padrao"]), step=0.5,
            help="Usado quando o veículo do motorista não informa o próprio rendimento.",
        )

        st.subheader("Regras de cálculo e jornada (RF10 / RN04)")
        coluna1, coluna2, coluna3 = st.columns(3)
        jornada = coluna1.number_input(
            "Jornada padrão (horas/dia)", value=float(atuais["jornada_horas"]), step=0.5,
            min_value=1.0, max_value=24.0,
        )
        tolerancia = coluna2.number_input(
            "Tolerância por parada (min)", value=float(atuais["tolerancia_minutos"]), step=1.0,
            min_value=0.0, help="Paradas abaixo desse tempo são desprezadas.",
        )
        arredondamento = coluna3.number_input(
            "Arredondamento (min)", value=int(atuais["arredondamento_minutos"]), step=1,
            min_value=0, max_value=60,
        )
        contar_partida = st.checkbox(
            "Contar tempo parado também no ponto de partida",
            value=bool(atuais["contar_ponto_partida"]),
            help="Desmarcado é o comportamento da RN01: a partida não acumula tempo.",
        )

        if st.form_submit_button("Aplicar configurações", type="primary"):
            try:
                api().atualizar_parametros(
                    {
                        "valor_combustivel": valor_combustivel,
                        "custo_por_km": custo_por_km,
                        "rendimento_km_l_padrao": rendimento_padrao,
                        "jornada_horas": jornada,
                        "tolerancia_minutos": tolerancia,
                        "arredondamento_minutos": arredondamento,
                        "contar_ponto_partida": contar_partida,
                    }
                )
                st.success("Parâmetros atualizados. Os cálculos já refletem os novos valores.")
            except ApiError as falha:
                erro(falha)

    if atuais.get("atualizado_em"):
        st.caption(
            f"Última alteração: {datetime.fromisoformat(atuais['atualizado_em']).strftime('%d/%m/%Y %H:%M')}"
            f" por {atuais.get('atualizado_por') or '—'}"
        )


# ---------------------------------------------------------------------------
# RNF04 / RNF05 — Administração
# ---------------------------------------------------------------------------
def pagina_administracao() -> None:
    st.title("Administração")
    st.caption("Usuários, perfis de acesso (RNF04) e trilha de auditoria (RNF05)")

    aba_usuarios, aba_auditoria, aba_dados = st.tabs(["Usuários", "Auditoria", "Dados"])

    with aba_usuarios:
        if usuario().get("perfil") != "administrador":
            st.info("Somente o administrador gerencia usuários.")
        else:
            _aba_usuarios()

    with aba_auditoria:
        try:
            eventos = api().auditoria(limite=300)
        except ApiError as falha:
            erro(falha)
            eventos = []
        if not eventos:
            st.caption("Nenhum evento registrado.")
        else:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Quando": datetime.fromisoformat(e["ocorrido_em"]).strftime(
                                "%d/%m/%Y %H:%M:%S"
                            ),
                            "Usuário": e.get("usuario_email") or "sistema",
                            "Perfil": e.get("perfil") or "—",
                            "Ação": e["acao"],
                            "Entidade": e["entidade"],
                            "ID": (e.get("entidade_id") or "")[:8],
                            "Detalhes": str(e.get("detalhes") or "")[:120],
                        }
                        for e in eventos
                    ]
                ),
                width="stretch", hide_index=True,
            )

    with aba_dados:
        st.write(
            "Popula a base com os roteiros de exemplo da especificação e um histórico "
            "sintético para o dashboard."
        )
        dias = st.slider("Dias de histórico", 30, 365, 120, step=30)
        if st.button("Executar carga de demonstração", type="primary"):
            with st.spinner("Gravando no Firestore..."):
                try:
                    resumo = api().seed(dias)
                    st.cache_data.clear()
                    st.success(f"Carga concluída: {resumo}")
                except ApiError as falha:
                    erro(falha)


def _aba_usuarios() -> None:
    try:
        motoristas = api().listar_motoristas()
        gerentes = api().listar_gerentes()
        usuarios = api().listar_usuarios()
    except ApiError as falha:
        erro(falha)
        return

    with st.form("form_usuario", clear_on_submit=True):
        coluna1, coluna2 = st.columns(2)
        nome = coluna1.text_input("Nome")
        email = coluna1.text_input("E-mail")
        senha = coluna2.text_input("Senha", type="password")
        perfil = coluna2.selectbox("Perfil", ["motorista", "gerente", "administrador"])

        vinculo_motorista = vinculo_gerente = None
        if perfil == "motorista" and motoristas:
            nomes = {m["nome"]: m["id"] for m in motoristas}
            vinculo_motorista = nomes[st.selectbox("Vincular ao motorista", list(nomes))]
        if perfil == "gerente" and gerentes:
            nomes = {g["nome"]: g["id"] for g in gerentes}
            vinculo_gerente = nomes[st.selectbox("Vincular ao gerente", list(nomes))]

        if st.form_submit_button("Criar usuário", type="primary"):
            try:
                api().criar_usuario(
                    {
                        "nome": nome,
                        "email": email,
                        "senha": senha,
                        "perfil": perfil,
                        "motorista_id": vinculo_motorista,
                        "gerente_id": vinculo_gerente,
                    }
                )
                st.success("Usuário criado.")
            except ApiError as falha:
                erro(falha)

    if usuarios:
        st.dataframe(
            pd.DataFrame(usuarios)[["nome", "email", "perfil", "ativo"]].rename(
                columns={"nome": "Nome", "email": "E-mail", "perfil": "Perfil", "ativo": "Ativo"}
            ),
            width="stretch", hide_index=True,
        )


# ---------------------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------------------
def main() -> None:
    if not st.session_state.get("token"):
        tela_login()
        return

    atual = usuario()
    st.sidebar.title("⏱️ ParouAí")
    st.sidebar.caption("Monitoramento de Tempo Parado")
    st.sidebar.divider()
    st.sidebar.markdown(f"**{atual.get('nome')}**  \n`{atual.get('perfil')}`")

    paginas = ["Dashboard", "Registro de Ponto", "Histórico"]
    if e_gestao():
        paginas += ["Cadastros", "Configurações", "Administração"]

    escolha = st.sidebar.radio("Navegação", paginas, label_visibility="collapsed")

    st.sidebar.divider()
    if st.sidebar.button("Sair", width="stretch"):
        st.session_state.clear()
        st.rerun()
    st.sidebar.caption("Engenharia de Software II · PUC Minas")

    try:
        if escolha == "Dashboard":
            pagina_dashboard()
        elif escolha == "Registro de Ponto":
            pagina_motorista()
        elif escolha == "Histórico":
            pagina_historico()
        elif escolha == "Cadastros":
            pagina_cadastros()
        elif escolha == "Configurações":
            pagina_configuracoes()
        elif escolha == "Administração":
            pagina_administracao()
    except ApiError as falha:
        if falha.status == 401:
            st.session_state.clear()
            st.warning("Sessão expirada. Entre novamente.")
            st.rerun()
        erro(falha)


main()
