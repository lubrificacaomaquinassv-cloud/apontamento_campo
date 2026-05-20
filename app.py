import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Apontamento de Campo - SIGCF", page_icon="🚜", layout="wide")

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    st.image("https://i.postimg.cc/Y9X7ddnb/LOGO-BP.jpg", width=110)
with col_titulo:
    st.title("Apontamento de Campo")
    st.caption("SIGCF - Sistema Integrado de Gestao de Custos de Frota")

st.divider()

# ─────────────────────────────────────────────
# CONEXÃO
# ─────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─────────────────────────────────────────────
# CARREGAMENTO
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def carregar_colaboradores():
    res = supabase.table("dim_colaborador")\
        .select("nome").eq("ativo", True)\
        .order("nome").execute()
    return [r["nome"] for r in (res.data or [])]

@st.cache_data(ttl=10)
def carregar_apontamentos(data_ini=None, data_fim=None, frota=None, operador=None):
    query = supabase.table("apontamento_campo").select("*")
    if data_ini:
        query = query.gte("data", str(data_ini))
    if data_fim:
        query = query.lte("data", str(data_fim))
    if frota:
        query = query.ilike("frota", f"%{frota}%")
    if operador and operador != "Todos":
        query = query.eq("operador", operador)
    res = query.order("data", desc=True).order("criado_em", desc=True).limit(200).execute()
    return res.data or []

colaboradores = carregar_colaboradores()

# ─────────────────────────────────────────────
# OPERAÇÕES / SUCÇÃO
# ─────────────────────────────────────────────
OPERACOES = [
    "Gradagem",
    "Plantio",
    "Colheita",
    "Pulverizacao",
    "Transporte",
    "Terraplenagem",
    "Roçagem",
    "Subsolagem",
    "Calagem",
    "Adubacao",
    "Irrigacao",
    "Manutencao de Estrada",
    "Carregamento",
    "Outra",
]

# ─────────────────────────────────────────────
# SIDEBAR — ÚLTIMOS LANÇAMENTOS
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://i.postimg.cc/Y9X7ddnb/LOGO-BP.jpg", width=140)
    st.divider()
    st.header("Últimos Lançamentos")
    ultimos = carregar_apontamentos()
    if ultimos:
        df_side = pd.DataFrame(ultimos)[
            ["data", "frota", "operador", "horas_trabalhadas"]
        ].head(10)
        df_side.columns = ["Data", "Frota", "Operador", "Horas"]
        st.dataframe(df_side, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum apontamento ainda.")

# ─────────────────────────────────────────────
# NAVEGAÇÃO
# ─────────────────────────────────────────────
pagina = st.tabs(["📝 Novo Apontamento", "📋 Consultar", "📊 Resumo por Frota"])

# ═══════════════════════════════════════════
# NOVO APONTAMENTO
# ═══════════════════════════════════════════
with pagina[0]:
    st.subheader("📝 Registrar Apontamento")

    with st.form("form_apontamento", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            data_ap  = st.date_input("📅 Data", value=date.today())
            operador = st.selectbox(
                "👤 Operador",
                options=colaboradores if colaboradores else ["Sem operadores cadastrados"]
            )
            frota    = st.text_input("🚜 Frota (Placa / ID)", placeholder="Ex: 3337 ou ABC-1234")

        with col2:
            h_inicial = st.number_input("⏱️ Horímetro Inicial", min_value=0.0,
                                        step=0.1, format="%.1f")
            h_final   = st.number_input("⏱️ Horímetro Final",   min_value=0.0,
                                        step=0.1, format="%.1f")
            horas     = round(h_final - h_inicial, 1)
            if horas > 0:
                st.metric("🕐 Horas Trabalhadas", f"{horas:.1f} h")
            elif h_final > 0 and horas <= 0:
                st.warning("⚠️ Horímetro final menor que inicial.")

        succao  = st.selectbox("⚙️ Operação / Sucção", options=OPERACOES)
        local   = st.text_input("📍 Local / Talhão", placeholder="Ex: Retiro Norte - Talhão 03")
        obs     = st.text_area("📝 Observação", height=60)

        submitted = st.form_submit_button("✅ Registrar Apontamento",
                                          use_container_width=True, type="primary")

    if submitted:
        if not frota.strip():
            st.error("⚠️ Informe a frota.")
        elif h_final <= h_inicial:
            st.error("⚠️ Horímetro final deve ser maior que o inicial.")
        elif not local.strip():
            st.error("⚠️ Informe o local.")
        else:
            novo = {
                "data":      str(data_ap),
                "operador":  operador,
                "frota":     frota.strip().upper(),
                "h_inicial": h_inicial,
                "h_final":   h_final,
                "succao":    succao,
                "local":     local.strip().upper(),
                "observacao": obs.strip() or None,
            }
            try:
                supabase.table("apontamento_campo").insert(novo).execute()
                st.success(f"✅ Apontamento salvo! {frota.upper()} | {operador} | {horas:.1f}h | {succao}")
                st.balloons()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# ═══════════════════════════════════════════
# CONSULTAR
# ═══════════════════════════════════════════
with pagina[1]:
    st.subheader("📋 Consultar Apontamentos")

    with st.expander("🔍 Filtros", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1: f_ini  = st.date_input("Data início", value=None, key="ci")
        with fc2: f_fim  = st.date_input("Data fim",    value=None, key="cf")
        with fc3: f_frt  = st.text_input("Frota (parcial)", key="ff")
        with fc4: f_op   = st.selectbox("Operador", ["Todos"] + colaboradores, key="fo")

    dados = carregar_apontamentos(
        f_ini, f_fim,
        f_frt if f_frt else None,
        f_op  if f_op != "Todos" else None
    )

    if not dados:
        st.info("Nenhum apontamento encontrado.")
    else:
        df = pd.DataFrame(dados)
        total_h = df["horas_trabalhadas"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Registros",        len(df))
        m2.metric("Total Horas Trabalhadas", f"{total_h:.1f} h")
        m3.metric("Frotas Únicas",           df["frota"].nunique())

        df_show = df[["data", "operador", "frota", "h_inicial",
                      "h_final", "horas_trabalhadas", "succao", "local", "observacao"]].copy()
        df_show.columns = ["Data", "Operador", "Frota", "H.Ini",
                           "H.Fin", "Horas", "Operação", "Local", "Obs"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # Export
        buf = df_show.copy()
        buf.to_excel("/tmp/apontamento_campo.xlsx", index=False)
        with open("/tmp/apontamento_campo.xlsx", "rb") as f:
            st.download_button(
                "⬇️ Exportar Excel",
                data=f,
                file_name=f"apontamento_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ═══════════════════════════════════════════
# RESUMO POR FROTA
# ═══════════════════════════════════════════
with pagina[2]:
    st.subheader("📊 Resumo por Frota")

    with st.expander("🔍 Período", expanded=True):
        r1, r2 = st.columns(2)
        with r1: r_ini = st.date_input("Data início", value=None, key="ri")
        with r2: r_fim = st.date_input("Data fim",    value=None, key="rf")

    dados_r = carregar_apontamentos(r_ini, r_fim)

    if not dados_r:
        st.info("Nenhum dado encontrado.")
    else:
        df_r = pd.DataFrame(dados_r)

        # Resumo por frota
        resumo = df_r.groupby("frota").agg(
            Registros=("id", "count"),
            Horas_Total=("horas_trabalhadas", "sum"),
            Operadores=("operador", "nunique"),
        ).reset_index().sort_values("Horas_Total", ascending=False)
        resumo["Horas_Total"] = resumo["Horas_Total"].apply(lambda x: f"{x:.1f} h")

        st.dataframe(resumo, use_container_width=True, hide_index=True)

        st.divider()

        # Gráfico horas por frota
        st.subheader("🚜 Horas por Frota")
        df_graf = df_r.groupby("frota")["horas_trabalhadas"].sum().reset_index()\
            .sort_values("horas_trabalhadas", ascending=False)
        st.bar_chart(df_graf.set_index("frota"))

        # Gráfico por operação
        st.subheader("⚙️ Horas por Operação")
        df_op = df_r.groupby("succao")["horas_trabalhadas"].sum().reset_index()\
            .sort_values("horas_trabalhadas", ascending=False)
        st.bar_chart(df_op.set_index("succao"))

        # Gráfico por operador
        st.subheader("👤 Horas por Operador")
        df_oper = df_r.groupby("operador")["horas_trabalhadas"].sum().reset_index()\
            .sort_values("horas_trabalhadas", ascending=False)
        st.bar_chart(df_oper.set_index("operador"))

st.divider()
st.caption("SIGCF | Apontamento de Campo | Nucleo de Controladoria SV")
