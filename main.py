#trabalho de eng de software 2

import random
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Monitoramento Logístico", layout="wide")

# ---------------------------------------------------------------------------
# DADOS SIMULADOS (MOCKS) - Substituir por chamadas ao Back-end (Banco de Dados)
# ---------------------------------------------------------------------------

def gerar_motoristas_mock():
    return [
        {"id": 1, "nome": "Carlos Silva", "telefone": "(31) 99999-0001",
         "documento": "123.456.789-00", "veiculo": "Moto Honda CG 160", "rendimento_km_l": 35.0},
        {"id": 2, "nome": "João Pereira", "telefone": "(31) 99999-0002",
         "documento": "987.654.321-00", "veiculo": "Fiorino", "rendimento_km_l": 10.5},
    ]

def gerar_roteiro_hoje_mock():
    hoje = datetime.now().date()
    return {
        "id": 1,
        "data": hoje,
        "motorista_id": 1,
        "distancia_estimada_km": 45.5,
        "pontos": [
            {"ordem": 1, "endereco": "Rua Seg. Família, 10 (Partida)", "chegada": None, "saida": None, "tempo_parado_min": 0},
            {"ordem": 2, "endereco": "Rua Peru, 55", "chegada": None, "saida": None, "tempo_parado_min": None},
            {"ordem": 3, "endereco": "Rua X, 5", "chegada": None, "saida": None, "tempo_parado_min": None},
        ],
    }

@st.cache_data
def gerar_serie_tempo_parado():
    random.seed(42)
    np.random.seed(42)
    dias = pd.date_range(end=datetime.now().date(), periods=180)
    linhas = []
    for d in dias:
        for _ in range(random.randint(1, 3)):
            linhas.append({
                "data": d,
                "motorista": random.choice(["Carlos Silva", "João Pereira"]),
                "tempo_parado_min": max(0, int(np.random.normal(65, 20))),
                "distancia_km": max(10, int(np.random.normal(50, 15))),
            })
    df = pd.DataFrame(linhas)
    df["mes"] = df["data"].dt.to_period("M").astype(str)
    return df

# ---------------------------------------------------------------------------
# INICIALIZAÇÃO DE ESTADO (SESSION STATE)
# ---------------------------------------------------------------------------

if "motoristas" not in st.session_state:
    st.session_state.motoristas = gerar_motoristas_mock()
if "rotas" not in st.session_state:
    st.session_state.rotas = []
if "roteiro_hoje" not in st.session_state:
    st.session_state.roteiro_hoje = gerar_roteiro_hoje_mock()

# RF09 e RF10: Parâmetros globais alteráveis pelo usuário
if "parametros" not in st.session_state:
    st.session_state.parametros = {
        "valor_combustivel": 5.85,
        "custo_fixo_km": 1.20,
        "jornada_horas": 8.0
    }

# ---------------------------------------------------------------------------
# TELAS DO SISTEMA
# ---------------------------------------------------------------------------

def pagina_dashboard(df):
    st.title("Dashboard Gerencial")
    st.markdown("Análise de Eficiência e Custos Logísticos")
    st.divider()

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            visao = st.selectbox("Recorte de Visualização", ["Por dia", "Por mês", "Por período"])
        with col2:
            motoristas_disp = ["Todos"] + sorted(df["motorista"].unique())
            filtro_motorista = st.selectbox("Filtrar Motorista", motoristas_disp)

    df_f = df if filtro_motorista == "Todos" else df[df["motorista"] == filtro_motorista]

    st.write("") 

    # Renderização de Gráficos
    if visao == "Por dia":
        agg = df_f.groupby("data", as_index=False)[["tempo_parado_min", "distancia_km"]].sum()
        fig = px.line(agg, x="data", y="tempo_parado_min", markers=True, title="Tempo Parado Total por Dia (min)")
    elif visao == "Por mês":
        agg = df_f.groupby("mes", as_index=False)[["tempo_parado_min", "distancia_km"]].sum()
        fig = px.bar(agg, x="mes", y="tempo_parado_min", title="Tempo Parado Total por Mês (min)", text_auto=True)
    else:
        c1, c2 = st.columns(2)
        with c1:
            inicio = st.date_input("Data Inicial", value=df_f["data"].min().date())
        with c2:
            fim = st.date_input("Data Final", value=df_f["data"].max().date())
            
        periodo = df_f[(df_f["data"] >= pd.to_datetime(inicio)) & (df_f["data"] <= pd.to_datetime(fim))]
        agg = periodo.groupby("data", as_index=False)[["tempo_parado_min", "distancia_km"]].sum()
        fig = px.bar(agg, x="data", y="tempo_parado_min", title=f"Tempo Parado no Período Selecionado (min)")

    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # RF11: Cálculos de Indicadores de Custo
    total_min = int(agg["tempo_parado_min"].sum())
    total_km = float(agg["distancia_km"].sum())
    
    jornada_min = st.session_state.parametros["jornada_horas"] * 60
    custo_combustivel_estimado = (total_km / 15.0) * st.session_state.parametros["valor_combustivel"] # Mock usando média de 15km/l
    
    with st.container(border=True):
        st.subheader("Indicadores do Período Selecionado")
        c1, c2, c3 = st.columns(3)
        c1.metric("Tempo Total Parado", f"{total_min} min")
        c2.metric("Impacto em Jornadas", f"{round(total_min / jornada_min, 1)} dias")
        c3.metric("Custo Est. de Combustível", f"R$ {custo_combustivel_estimado:,.2f}")


def pagina_motorista(motoristas):
    st.title("Registro de Ponto")
    st.markdown("Painel Operacional do Entregador")
    st.divider()

    nomes = {m["id"]: m["nome"] for m in motoristas}
    motorista_id = st.selectbox(
        "Autenticação de Usuário",
        list(nomes.keys()), format_func=lambda i: nomes[i],
    )

    roteiro = st.session_state.roteiro_hoje
    if roteiro["motorista_id"] != motorista_id:
        st.info("Nenhum roteiro ativo atribuído a este motorista para a data de hoje.")
        return

    pontos = roteiro["pontos"]
    proximo = next((p for p in pontos if p["chegada"] is None), None)

    st.subheader(f"Roteiro: {roteiro['data'].strftime('%d/%m/%Y')} | Distância Est: {roteiro['distancia_estimada_km']} km")
    
    with st.container(border=True):
        for p in pontos:
            if p["saida"]:
                status = "Concluído"
            elif p["chegada"]:
                status = "Em andamento"
            else:
                status = "Pendente"
            st.markdown(f"**Ponto {p['ordem']}** | {p['endereco']} | Status: `{status}`")

    st.write("")

    if proximo is None:
        st.success("Todos os pontos do roteiro foram concluídos com sucesso.")
        total = sum(p["tempo_parado_min"] or 0 for p in pontos)
        st.metric("Tempo Total Parado no Roteiro", f"{total} min")
        return

    with st.container(border=True):
        st.markdown(f"### Ponto Atual: {proximo['endereco']}")
        col1, col2 = st.columns(2)

        with col1:
            if proximo["chegada"] is None:
                if st.button("Registrar Chegada", use_container_width=True, type="primary"):
                    proximo["chegada"] = datetime.now()
                    st.rerun()
            else:
                st.write(f"**Horário de Chegada:** {proximo['chegada'].strftime('%H:%M:%S')}")

        with col2:
            if proximo["chegada"] is not None and proximo["saida"] is None:
                if st.button("Registrar Saída", use_container_width=True, type="primary"):
                    proximo["saida"] = datetime.now()
                    if proximo["ordem"] == 1:
                        proximo["tempo_parado_min"] = 0 
                    else:
                        delta = proximo["saida"] - proximo["chegada"]
                        proximo["tempo_parado_min"] = round(delta.total_seconds() / 60, 1) 
                    st.rerun()
            elif proximo["saida"] is not None:
                st.write(f"**Horário de Saída:** {proximo['saida'].strftime('%H:%M:%S')}")
                st.write(f"**Tempo Parado:** {proximo['tempo_parado_min']} min")


def pagina_cadastros():
    st.title("Gestão de Entidades")
    st.markdown("Cadastros estruturais do sistema")
    st.divider()

    aba1, aba2 = st.tabs(["Cadastro de Motoristas", "Planejamento de Rotas"])

    with aba1:
        with st.form("form_motorista", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome Completo")
                documento = st.text_input("Documento (CPF/CNH)")
            with col2:
                telefone = st.text_input("Telefone de Contato")
                veiculo = st.text_input("Veículo")
            
            rendimento = st.number_input("Rendimento do Veículo (km/litro)", min_value=0.0, step=0.5)
            enviado = st.form_submit_button("Salvar Motorista", type="primary")

        if enviado and nome:
            novo_id = max((m["id"] for m in st.session_state.motoristas), default=0) + 1
            st.session_state.motoristas.append({
                "id": novo_id, "nome": nome, "telefone": telefone,
                "documento": documento, "veiculo": veiculo, "rendimento_km_l": rendimento,
            })
            st.success("Motorista cadastrado com sucesso.")

        st.dataframe(pd.DataFrame(st.session_state.motoristas), use_container_width=True, hide_index=True)

    with aba2:
        nomes = {m["id"]: m["nome"] for m in st.session_state.motoristas}
        with st.form("form_rota", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data_rota = st.date_input("Data de Execução", value=datetime.now().date())
            with col2:
                motorista_id = st.selectbox("Motorista Responsável", list(nomes.keys()), format_func=lambda i: nomes[i])
            
            enderecos_txt = st.text_area(
                "Endereços do Trajeto (Primeira linha define a partida)",
                placeholder="Rua A, 100\nAvenida B, 200", height=100,
            )
            enviado = st.form_submit_button("Gerar Roteiro", type="primary")

        if enviado:
            enderecos = [e.strip() for e in enderecos_txt.splitlines() if e.strip()]
            if len(enderecos) > 1:
                pontos = [
                    {"ordem": i + 1, "endereco": e, "chegada": None, "saida": None, "tempo_parado_min": 0 if i == 0 else None}
                    for i, e in enumerate(enderecos)
                ]
                nova_rota = {"id": len(st.session_state.rotas) + 1, "data": data_rota, "motorista_id": motorista_id, "pontos": pontos}
                st.session_state.rotas.append(nova_rota)
                st.success(f"Roteiro processado. Paradas: {len(pontos)}")

        if st.session_state.rotas:
            for r in st.session_state.rotas:
                with st.container(border=True):
                    st.write(f"**ID:** {r['id']} | **Motorista:** {nomes.get(r['motorista_id'], '?')} | **Data:** {r['data'].strftime('%d/%m/%Y')} | **Pontos:** {len(r['pontos'])}")


def pagina_configuracoes():
    st.title("Configurações do Sistema")
    st.markdown("Ajuste de parâmetros de negócio e custos operacionais (RF09, RF10)")
    st.divider()

    with st.container(border=True):
        st.subheader("Parâmetros Globais")
        with st.form("form_parametros"):
            col1, col2 = st.columns(2)
            
            with col1:
                novo_combustivel = st.number_input(
                    "Valor do Combustível (R$/Litro)", 
                    value=st.session_state.parametros["valor_combustivel"], 
                    step=0.10
                )
                novo_custo_km = st.number_input(
                    "Custo Operacional por KM (R$)", 
                    value=st.session_state.parametros["custo_fixo_km"], 
                    step=0.10
                )
                
            with col2:
                nova_jornada = st.number_input(
                    "Jornada Padrão de Trabalho (Horas/Dia)", 
                    value=st.session_state.parametros["jornada_horas"], 
                    step=1.0
                )
                
            salvar = st.form_submit_button("Aplicar Configurações", type="primary", use_container_width=True)
            
            if salvar:
                st.session_state.parametros = {
                    "valor_combustivel": novo_combustivel,
                    "custo_fixo_km": novo_custo_km,
                    "jornada_horas": nova_jornada
                }
                st.success("Parâmetros atualizados com sucesso. Os dashboards refletirão os novos valores.")

# ---------------------------------------------------------------------------
# NAVEGAÇÃO LATERAL
# ---------------------------------------------------------------------------

st.sidebar.title("Sistema Logístico")
st.sidebar.markdown("Gestão de Tempo Parado")
st.sidebar.divider()

pagina = st.sidebar.radio(
    "Navegação",
    ["Dashboard Gerencial", "App do Motorista", "Cadastros", "Configurações"],
)

st.sidebar.divider()
st.sidebar.caption("Projeto Acadêmico | Engenharia de Software II")
st.sidebar.caption("PUC Minas")

df_serie = gerar_serie_tempo_parado()

if pagina == "Dashboard Gerencial":
    pagina_dashboard(df_serie)
elif pagina == "App do Motorista":
    pagina_motorista(st.session_state.motoristas)
elif pagina == "Cadastros":
    pagina_cadastros()
elif pagina == "Configurações":
    pagina_configuracoes()