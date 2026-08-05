import re
import streamlit as st
import pandas as pd
from datetime import date, time
from io import BytesIO
from supabase import create_client

st.set_page_config(
    page_title="Apontamento de Campo - SIGCF",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from sigcf_auth import exigir_acesso, logo_html

exigir_acesso("Apontamento de Campo")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');
[data-testid="stAppViewContainer"]{background:#0a1409;}
[data-testid="stSidebar"]{background:#111c10;border-right:1px solid #1e2e1c;}
[data-testid="stHeader"]{background:#0a1409;}
h1,h2,h3,h4,p,span,label{color:#e8edd0;}
h1{font-family:'Barlow Condensed',sans-serif;letter-spacing:1px;}
.stCaption,[data-testid="stCaptionContainer"] p{color:#8aab80!important;}
.sec{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
 letter-spacing:2px;text-transform:uppercase;color:#8aab80;
 border-left:4px solid #4a9e3f;padding-left:10px;margin:8px 0 12px;}
.logo-frame{background:linear-gradient(145deg,#0a1628,#0d2040);border:2px solid #c9a227;
 border-radius:12px;padding:5px;display:inline-block;box-shadow:0 4px 18px rgba(0,0,0,.45);}
.logo-frame img{display:block;border-radius:8px;}

.stTextInput input,.stNumberInput input,.stTextArea textarea,
[data-testid="stDateInput"] input{
 background:#dce6d2!important;color:#1a2818!important;
 border:1px solid #4a6644!important;border-radius:8px!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus,
[data-testid="stDateInput"] input:focus{
 border-color:#6fcf60!important;box-shadow:0 0 0 1px #6fcf6044!important;}
div[data-baseweb="select"] > div{
 background:#dce6d2!important;border:1px solid #4a6644!important;
 color:#1a2818!important;border-radius:8px!important;}
div[data-baseweb="select"] div{color:#1a2818!important;}
div[data-baseweb="select"] svg{fill:#4a6644!important;}
ul[data-testid="stSelectboxVirtualDropdown"],
div[data-baseweb="popover"] ul{background:#e8edd0!important;}
div[data-baseweb="popover"] li{color:#1a2818!important;}
[data-testid="stNumberInput"] button{
 background:#cdd9c4!important;border-color:#4a6644!important;color:#1a2818!important;}
[data-testid="stForm"]{
 background:#0d180c!important;border:1px solid #1e2e1c!important;
 border-radius:12px;padding:12px 16px;}
[data-testid="stVerticalBlockBorderWrapper"]{
 background:#0d180c!important;border-color:#1e2e1c!important;}
div[data-testid="stMetric"]{background:#0d180c;border:1px solid #1e2e1c;border-radius:10px;padding:10px 14px;}
div[data-testid="stMetric"] label{color:#8aab80!important;}
div[data-testid="stMetricValue"]{color:#6fcf60!important;font-family:'Barlow Condensed',sans-serif;}

.stTabs [data-baseweb="tab-list"]{background:#0d180c;border-bottom:1px solid #1e2e1c;gap:8px;}
.stTabs [data-baseweb="tab"]{
 color:#8aab80!important;font-family:'Barlow Condensed',sans-serif;
 font-weight:600;letter-spacing:0.5px;}
.stTabs [aria-selected="true"]{
 color:#e8edd0!important;border-bottom-color:#4a9e3f!important;}
[data-testid="stExpander"]{
 background:#0d180c!important;border:1px solid #1e2e1c!important;border-radius:10px;}
[data-testid="stExpander"] summary{color:#e8edd0!important;}
.stTabs [data-baseweb="tab-highlight"]{background-color:#4a9e3f!important;}
.stButton button,[data-testid="stFormSubmitButton"] button{
 background:#4a9e3f!important;color:#ffffff!important;border:1px solid #6fcf60!important;
 font-family:'Barlow Condensed',sans-serif;font-weight:700;letter-spacing:1.5px;
 text-transform:uppercase;border-radius:8px;}
.stButton button:hover,[data-testid="stFormSubmitButton"] button:hover{background:#3d8534!important;}
.stButton button p,[data-testid="stFormSubmitButton"] button p{color:#ffffff!important;}
</style>
""", unsafe_allow_html=True)


def dark_table(df, height=260):
    if df.empty:
        st.info("Nenhum registro.")
        return
    rows = "".join(
        "<tr>" + "".join(
            f'<td style="padding:6px 10px;border-bottom:1px solid #1e2e1c;'
            f'color:#e8edd0;font-size:12px;white-space:nowrap;">{v}</td>'
            for v in row) + "</tr>"
        for _, row in df.iterrows())
    headers = "".join(
        f'<th style="padding:7px 10px;background:#111c10;color:#8aab80;font-size:10px;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:1px;'
        f'border-bottom:2px solid #1e2e1c;white-space:nowrap;">{c}</th>'
        for c in df.columns)
    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid #1e2e1c;border-radius:10px;">'
        f'<div style="max-height:{height}px;overflow-y:auto;">'
        f'<table style="width:100%;border-collapse:collapse;background:#0d180c;'
        f'font-family:Barlow Condensed,sans-serif;"><thead><tr>{headers}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div></div>',
        unsafe_allow_html=True,
    )


def gerar_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def fmt_hora(t):
    """time ou string HH:MM → 'HH:MM' ou None."""
    if t is None:
        return None
    if isinstance(t, time):
        return t.strftime("%H:%M")
    s = str(t).strip()
    if not s:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return f"{h:02d}:{mi:02d}"
    return None


def parse_hora_txt(txt):
    """Aceita HH:MM ou vazio."""
    return fmt_hora(txt)


def montar_insumo(insumo, qtd, unidade, extras):
    """Monta texto de insumo (principal + adicionais). None se vazio."""
    partes = []
    ins = str(insumo or "").strip()
    if ins:
        if qtd is not None and qtd > 0 and unidade and unidade != "—":
            partes.append(f"{ins} {qtd:g} {unidade}")
        else:
            partes.append(ins)
    ext = str(extras or "").strip()
    if ext:
        partes.append(ext)
    return " | ".join(partes) if partes else None


def parse_qtd_insumo(txt):
    """Quantidade opcional — vazio permanece None."""
    s = str(txt or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        v = float(s)
        return v if v > 0 else None
    except ValueError:
        return None


def campos_insumo(insumo, qtd_txt, unidade, extras):
    """
    Retorna insumo / quantidade_insumo / unidade para o INSERT.
    Sem informe de defensivo ou insumo → todos None (NULL no banco).
    """
    ins = str(insumo or "").strip()
    ext = str(extras or "").strip()
    qtd = parse_qtd_insumo(qtd_txt)

    if not ins and not ext:
        return {"insumo": None, "quantidade_insumo": None, "unidade": None}

    texto = montar_insumo(insumo, qtd, unidade, extras)
    qtd_db = None
    un_db = None
    if ins and qtd is not None and unidade and unidade != "—":
        qtd_db = qtd
        un_db = unidade

    return {"insumo": texto, "quantidade_insumo": qtd_db, "unidade": un_db}


def nulo_se_vazio(val):
    """Texto vazio → None (NULL). Horários já vêm None quando em branco."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def montar_observacao(obs, almoco, retorno):
    """Observação livre + almoço/retorno opcionais."""
    linhas = []
    if almoco:
        linhas.append(f"Almoço {almoco}")
    if retorno:
        linhas.append(f"Retorno {retorno}")
    base = str(obs or "").strip()
    if base:
        linhas.append(base)
    return "\n".join(linhas) if linhas else None


COLUNAS_CONSULTA = [
    "data", "operador", "frota", "succao", "talhoes", "local",
    "inicio_turno", "fim_turno", "inicio_operacao", "fim_operacao",
    "h_inicial", "h_final", "horas_trabalhadas",
    "insumo", "quantidade_insumo", "unidade", "observacao",
]
LABELS_CONSULTA = {
    "data": "Data", "operador": "Operador", "frota": "Frota",
    "succao": "Operação", "talhoes": "Talhão(ões)", "local": "Local",
    "inicio_turno": "Início turno", "fim_turno": "Fim turno",
    "inicio_operacao": "Início oper.", "fim_operacao": "Fim oper.",
    "h_inicial": "H.Ini", "h_final": "H.Fin", "horas_trabalhadas": "Horas",
    "insumo": "Insumo", "quantidade_insumo": "Qtd", "unidade": "Un.",
    "observacao": "Obs",
}

UNIDADES_INSUMO = ["—", "ml", "L", "lts", "kg", "g", "GM", "UN"]

OPERACOES_SEM_INSUMO_HINT = (
    "Gradagem, rocagem, transporte, limpeza e similares — **sem** adubo, defensivo ou calda."
)


# ─────────────────────────────────────────────
# CONEXÃO
# ─────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_data(ttl=60)
def carregar_colaboradores():
    try:
        res = (
            supabase.table("dim_colaborador")
            .select("nome")
            .eq("ativo", True)
            .order("nome")
            .execute()
        )
        return [r["nome"] for r in (res.data or [])]
    except Exception as e:
        st.error(f"Erro ao carregar operadores (dim_colaborador): {e}")
        return []


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
    res = (
        query.order("data", desc=True)
        .order("criado_em", desc=True)
        .limit(200)
        .execute()
    )
    return res.data or []


def ultimos_lancamentos_df(limit=12):
    rows = carregar_apontamentos()[:limit]
    if not rows:
        return pd.DataFrame()
    rename = {
        "data": "Data",
        "frota": "Frota",
        "operador": "Operador",
        "succao": "Operação",
        "talhoes": "Talhão",
        "horas_trabalhadas": "Horas",
        "inicio_operacao": "Início op.",
        "fim_operacao": "Fim op.",
    }
    df = pd.DataFrame(rows)
    cols = [c for c in rename if c in df.columns]
    out = df[cols].rename(columns=rename)
    if "Horas" in out.columns:
        out["Horas"] = out["Horas"].apply(lambda v: f"{float(v):.1f} h" if pd.notna(v) else "—")
    return out


def rodape_ultimos_lancamentos():
    st.divider()
    st.markdown('<div class="sec">Últimos lançamentos</div>', unsafe_allow_html=True)
    dark_table(ultimos_lancamentos_df(), height=200)
    st.caption("SIGCF | Apontamento de Campo | Núcleo de Controladoria SV")


OPERACOES = [
    "GRADAGEM", "PLANTIO", "CORTE DE EUCALIPTO", "PULVERIZACAO", "TERRAPLANAGEM",
    "ROCAGEM", "SUBSOLAGEM", "CALAGEM", "ADUBACAO", "IRRIGACAO",
    "MANUTENCAO DE ESTRADA", "LIMPEZA DE RANK", "MARCACAO DE PASTORIL", "CONCEICAO",
    "CAPINA QUIMICA", "LAMININHA", "COLETA DE RESIDUOS", "CARRETA DO SAL",
    "LIMPEZA DE RUA DA SULCACAO", "PIPINHA DO PLANTIO", "ENCABECAMENTO DE CURVA",
    "REMOCAO DE CERCA", "ENTERRANDO ANIMAIS", "CARREGAR ADUBO", "LIMPEZA DE CERVA",
    "TRATO", "CARREGAR CALCARIO", "TERRAPLANAGEM RURAL", "COMBATE INCENDIO",
    "CONTROLE DE FORMIGA", "ACEIRO DE FLORESTA", "CARREADOR DE FLORESTA",
    "HERCULES", "PUXAR LINK", "FENO", "LIMPEZA DE BAIA", "ESPLANADA",
    "SERVICOS DIVERSOS", "LIMPEZA DE COCHO", "OUTRA",
]

colaboradores = carregar_colaboradores()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_logo, col_titulo = st.columns([1.1, 5.9])
with col_logo:
    st.markdown(logo_html(118), unsafe_allow_html=True)
with col_titulo:
    st.title("Apontamento de Campo")
    st.caption("SIGCF — Sistema Integrado de Gestão de Custos de Frota")

pagina = st.tabs(["📝 Novo Apontamento", "📋 Consultar", "📊 Resumo por Frota"])

# ═══════════════════════════════════════════
# NOVO APONTAMENTO
# ═══════════════════════════════════════════
with pagina[0]:
    st.markdown('<div class="sec">Registrar apontamento</div>', unsafe_allow_html=True)

    with st.form("form_apontamento", clear_on_submit=True):
        st.markdown("**Identificação**")
        col1, col2, col3 = st.columns(3)
        with col1:
            data_ap = st.date_input("📅 Data", value=date.today())
        with col2:
            frota = st.text_input("🚜 Frota (ID)", placeholder="Ex: 3396")
        with col3:
            operador = st.selectbox(
                "👤 Operador",
                options=colaboradores if colaboradores else ["Sem operadores cadastrados"],
            )

        st.markdown("**Operação**")
        c_op1, c_op2 = st.columns(2)
        with c_op1:
            succao = st.selectbox("⚙️ Operação", options=OPERACOES)
        with c_op2:
            talhoes = st.text_input(
                "🌾 Talhão(ões) / área",
                placeholder="Ex: córrego do campo pasto 547",
            )
        local = st.text_input(
            "📍 Local complementar (opcional)",
            placeholder="Ex: Retiro Norte — use se quiser detalhar além do talhão",
        )

        st.markdown("**Horários da operação**")
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            inicio_operacao = st.text_input("▶ Início operação", placeholder="08:20")
        with t2:
            fim_operacao = st.text_input("⏹ Fim operação", placeholder="17:00")
        with t3:
            inicio_turno = st.text_input("▶ Início turno", placeholder="06:31")
        with t4:
            fim_turno = st.text_input("⏹ Fim turno", placeholder="18:14")

        st.markdown("**Horímetro**")
        h1, h2, h3 = st.columns(3)
        with h1:
            h_inicial = st.number_input("Horímetro inicial", min_value=0.0, step=0.1, format="%.1f")
        with h2:
            h_final = st.number_input("Horímetro final", min_value=0.0, step=0.1, format="%.1f")
        with h3:
            horas = round(h_final - h_inicial, 1)
            if horas > 0:
                st.metric("Horas (horímetro)", f"{horas:.1f} h")
            elif h_final > 0 and horas <= 0:
                st.warning("Horímetro final menor que inicial.")

        st.markdown("**Intervalo (opcional)**")
        a1, a2 = st.columns(2)
        with a1:
            almoco = st.text_input("🍽 Almoço (saída)", placeholder="11:35")
        with a2:
            retorno = st.text_input("↩ Retorno", placeholder="12:26")

        with st.expander("🧪 Insumos / Defensivos (opcional)", expanded=False):
            st.caption(
                "Preencha **somente** quando houve aplicação de adubo, defensivo, calda ou similar. "
                + OPERACOES_SEM_INSUMO_HINT
                + " Se não houve aplicação, deixe tudo em branco — nada será gravado no banco."
            )
            i1, i2, i3 = st.columns([2, 1, 1])
            with i1:
                insumo = st.text_input(
                    "Insumo / defensivo principal",
                    placeholder="Ex: fipronil (deixe vazio se não aplicou)",
                )
            with i2:
                quantidade_insumo = st.text_input(
                    "Quantidade",
                    placeholder="Ex: 0.150",
                )
            with i3:
                unidade = st.selectbox("Unidade", options=UNIDADES_INSUMO)
            insumos_extras = st.text_area(
                "Outros insumos ou calda",
                placeholder="Ex: Fordor 0.300 GM | 800 lts calda",
            )

        obs = st.text_area("📝 Observação")
        submitted = st.form_submit_button("✅ Registrar Apontamento", use_container_width=True, type="primary")

    if submitted:
        hi_op = parse_hora_txt(inicio_operacao)
        hf_op = parse_hora_txt(fim_operacao)
        hi_turno = parse_hora_txt(inicio_turno)
        hf_turno = parse_hora_txt(fim_turno)
        hi_almoco = parse_hora_txt(almoco)
        hi_retorno = parse_hora_txt(retorno)

        erros = []
        if not frota.strip():
            erros.append("Informe a frota.")
        if h_final <= h_inicial:
            erros.append("Horímetro final deve ser maior que o inicial.")
        if not talhoes.strip() and not local.strip():
            erros.append("Informe o talhão ou local.")
        for lbl, val, raw in [
            ("Início operação", hi_op, inicio_operacao),
            ("Fim operação", hf_op, fim_operacao),
            ("Início turno", hi_turno, inicio_turno),
            ("Fim turno", hf_turno, fim_turno),
            ("Almoço", hi_almoco, almoco),
            ("Retorno", hi_retorno, retorno),
        ]:
            if str(raw or "").strip() and not val:
                erros.append(f"{lbl}: use HH:MM (ex: 08:20).")

        if erros:
            for e in erros:
                st.error(f"⚠️ {e}")
        else:
            ins = campos_insumo(insumo, quantidade_insumo, unidade, insumos_extras)

            novo = {
                "data": str(data_ap),
                "operador": operador,
                "frota": frota.strip().upper(),
                "h_inicial": h_inicial,
                "h_final": h_final,
                "succao": succao,
                "talhoes": nulo_se_vazio(talhoes.strip().upper() if talhoes else ""),
                "local": nulo_se_vazio(local.strip().upper() if local else ""),
                "inicio_turno": hi_turno,
                "fim_turno": hf_turno,
                "inicio_operacao": hi_op,
                "fim_operacao": hf_op,
                "insumo": ins["insumo"],
                "quantidade_insumo": ins["quantidade_insumo"],
                "unidade": ins["unidade"],
                "observacao": montar_observacao(obs, hi_almoco, hi_retorno),
            }
            try:
                supabase.table("apontamento_campo").insert(novo).execute()
                st.success(
                    f"✅ Apontamento salvo! {frota.upper()} | {operador} | {horas:.1f}h | {succao}"
                )
                st.balloons()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# ═══════════════════════════════════════════
# CONSULTAR
# ═══════════════════════════════════════════
with pagina[1]:
    st.markdown('<div class="sec">Consultar apontamentos</div>', unsafe_allow_html=True)

    with st.expander("🔍 Filtros", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            f_ini = st.date_input("Data início", value=None, key="ci")
        with fc2:
            f_fim = st.date_input("Data fim", value=None, key="cf")
        with fc3:
            f_frt = st.text_input("Frota (parcial)", key="ff")
        with fc4:
            f_op = st.selectbox("Operador", ["Todos"] + colaboradores, key="fo")

    dados = carregar_apontamentos(
        f_ini, f_fim,
        f_frt if f_frt else None,
        f_op if f_op != "Todos" else None,
    )

    if not dados:
        st.info("Nenhum apontamento encontrado.")
    else:
        df = pd.DataFrame(dados)
        total_h = df["horas_trabalhadas"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Registros", len(df))
        m2.metric("Total Horas Trabalhadas", f"{total_h:.1f} h")
        m3.metric("Frotas Únicas", df["frota"].nunique())

        cols_disp = [c for c in COLUNAS_CONSULTA if c in df.columns]
        df_show = df[cols_disp].copy()
        df_show.columns = [LABELS_CONSULTA.get(c, c) for c in cols_disp]
        dark_table(df_show.head(50), height=360)

        st.download_button(
            "⬇️ Exportar Excel",
            data=gerar_excel(df_show),
            file_name=f"apontamento_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ═══════════════════════════════════════════
# RESUMO POR FROTA
# ═══════════════════════════════════════════
with pagina[2]:
    st.markdown('<div class="sec">Resumo por frota</div>', unsafe_allow_html=True)

    with st.expander("🔍 Período", expanded=True):
        r1, r2 = st.columns(2)
        with r1:
            r_ini = st.date_input("Data início", value=None, key="ri")
        with r2:
            r_fim = st.date_input("Data fim", value=None, key="rf")

    dados_r = carregar_apontamentos(r_ini, r_fim)

    if not dados_r:
        st.info("Nenhum dado encontrado.")
    else:
        df_r = pd.DataFrame(dados_r)
        resumo = (
            df_r.groupby("frota")
            .agg(
                Registros=("id", "count"),
                Horas_Total=("horas_trabalhadas", "sum"),
                Operadores=("operador", "nunique"),
            )
            .reset_index()
            .sort_values("Horas_Total", ascending=False)
        )
        resumo["Horas_Total"] = resumo["Horas_Total"].apply(lambda x: f"{x:.1f} h")
        dark_table(resumo, height=280)

        st.markdown('<div class="sec">Horas por frota</div>', unsafe_allow_html=True)
        df_graf = (
            df_r.groupby("frota")["horas_trabalhadas"]
            .sum()
            .reset_index()
            .sort_values("horas_trabalhadas", ascending=False)
        )
        st.bar_chart(df_graf.set_index("frota"))

        st.markdown('<div class="sec">Horas por operação</div>', unsafe_allow_html=True)
        df_op = (
            df_r.groupby("succao")["horas_trabalhadas"]
            .sum()
            .reset_index()
            .sort_values("horas_trabalhadas", ascending=False)
        )
        st.bar_chart(df_op.set_index("succao"))

        st.markdown('<div class="sec">Horas por operador</div>', unsafe_allow_html=True)
        df_oper = (
            df_r.groupby("operador")["horas_trabalhadas"]
            .sum()
            .reset_index()
            .sort_values("horas_trabalhadas", ascending=False)
        )
        st.bar_chart(df_oper.set_index("operador"))

rodape_ultimos_lancamentos()
