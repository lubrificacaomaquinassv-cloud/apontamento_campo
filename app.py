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
/* Tema teste Lovable + Segoe UI (Apontamento Campo) */
:root{
 --sigcf-bg:#0a1409;--sigcf-card:#0f1f12;--sigcf-border:#2a4030;
 --sigcf-text:#e8edd0;--sigcf-label:#8aab80;--sigcf-green:#6fcf60;
 --sigcf-gold:#ffd966;--sigcf-ouro:#c9a227;
 --sigcf-font:'Segoe UI','Segoe UI Variable',system-ui,-apple-system,sans-serif;
}
html,body,[class*="css"]{font-family:var(--sigcf-font)!important;}
[data-testid="stAppViewContainer"]{background:var(--sigcf-bg);}
[data-testid="stSidebar"]{background:#111c10;border-right:1px solid var(--sigcf-border);}
[data-testid="stHeader"]{background:var(--sigcf-bg);}
h1,h2,h3,h4,p,span,label,div{color:var(--sigcf-text);}
h1,h2,h3,h4{
 font-family:var(--sigcf-font)!important;font-weight:600;letter-spacing:0.02em;}
h1{font-size:1.75rem;}
.stCaption,[data-testid="stCaptionContainer"] p{
 color:var(--sigcf-label)!important;font-family:var(--sigcf-font)!important;}
.sec{
 font-family:var(--sigcf-font)!important;font-size:12px;font-weight:600;
 letter-spacing:0.12em;text-transform:uppercase;color:var(--sigcf-gold);
 border-left:4px solid var(--sigcf-green);padding-left:10px;margin:8px 0 12px;}
.logo-frame{background:linear-gradient(145deg,#0a1628,#0d2040);border:2px solid var(--sigcf-ouro);
 border-radius:12px;padding:5px;display:inline-block;box-shadow:0 4px 18px rgba(0,0,0,.45);}
.logo-frame img{display:block;border-radius:8px;}

.stTextInput input,.stNumberInput input,.stTextArea textarea,
[data-testid="stDateInput"] input{
 background:#dce6d2!important;color:#1a2818!important;
 border:1px solid var(--sigcf-border)!important;border-radius:8px!important;
 font-family:var(--sigcf-font)!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus,
[data-testid="stDateInput"] input:focus{
 border-color:var(--sigcf-green)!important;box-shadow:0 0 0 1px rgba(111,207,96,.35)!important;}
div[data-baseweb="select"] > div{
 background:#dce6d2!important;border:1px solid var(--sigcf-border)!important;
 color:#1a2818!important;border-radius:8px!important;
 font-family:var(--sigcf-font)!important;}
div[data-baseweb="select"] div{color:#1a2818!important;}
div[data-baseweb="select"] svg{fill:#4a6644!important;}
ul[data-testid="stSelectboxVirtualDropdown"],
div[data-baseweb="popover"] ul{background:#e8edd0!important;}
div[data-baseweb="popover"] li{color:#1a2818!important;font-family:var(--sigcf-font)!important;}
[data-testid="stNumberInput"] button{
 background:#cdd9c4!important;border-color:var(--sigcf-border)!important;color:#1a2818!important;}
[data-testid="stForm"]{
 background:var(--sigcf-card)!important;border:1px solid var(--sigcf-border)!important;
 border-radius:12px;padding:12px 16px;}
[data-testid="stVerticalBlockBorderWrapper"]{
 background:var(--sigcf-card)!important;border-color:var(--sigcf-border)!important;}
div[data-testid="stMetric"]{
 background:var(--sigcf-card);border:1px solid var(--sigcf-border);
 border-left:4px solid var(--sigcf-green);border-radius:8px;padding:12px 16px;}
div[data-testid="stMetric"] label{
 color:var(--sigcf-label)!important;font-family:var(--sigcf-font)!important;
 font-size:11px!important;letter-spacing:0.1em!important;text-transform:uppercase!important;}
div[data-testid="stMetricValue"]{
 color:var(--sigcf-gold)!important;font-family:var(--sigcf-font)!important;
 font-weight:700!important;font-size:1.6rem!important;}

.stTabs [data-baseweb="tab-list"]{
 background:var(--sigcf-card);border-bottom:1px solid var(--sigcf-border);gap:8px;}
.stTabs [data-baseweb="tab"]{
 color:var(--sigcf-label)!important;font-family:var(--sigcf-font)!important;
 font-weight:600;letter-spacing:0.12em;text-transform:uppercase;}
.stTabs [aria-selected="true"]{
 color:var(--sigcf-green)!important;border-bottom:3px solid var(--sigcf-green)!important;}
[data-testid="stExpander"]{
 background:var(--sigcf-card)!important;border:1px solid var(--sigcf-border)!important;border-radius:10px;}
[data-testid="stExpander"] summary{
 color:var(--sigcf-text)!important;font-family:var(--sigcf-font)!important;}
.stTabs [data-baseweb="tab-highlight"]{background-color:var(--sigcf-green)!important;}
.stButton button,[data-testid="stFormSubmitButton"] button{
 background:#4a9e3f!important;color:#ffffff!important;border:1px solid var(--sigcf-green)!important;
 font-family:var(--sigcf-font)!important;font-weight:600;letter-spacing:0.08em;
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
        f'font-family:Segoe UI,sans-serif;"><thead><tr>{headers}</tr></thead>'
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


_UNIDADES_RE = r"ml|lts?|L|kg|g|GM|UN"


def _parse_item_insumo(texto):
    """Extrai produto, quantidade e unidade de um fragmento de texto."""
    s = str(texto or "").strip()
    if not s:
        return None
    m = re.match(
        rf"^(.+?)\s+([\d,\.]+)\s*({_UNIDADES_RE})\s*$",
        s,
        re.IGNORECASE,
    )
    if m:
        qtd = parse_qtd_insumo(m.group(2))
        if qtd is not None:
            return {
                "produto": m.group(1).strip(),
                "quantidade": qtd,
                "unidade": m.group(3).upper().replace("LTS", "L"),
            }
    m = re.match(
        rf"^([\d,\.]+)\s*({_UNIDADES_RE})\s+(.+)$",
        s,
        re.IGNORECASE,
    )
    if m:
        qtd = parse_qtd_insumo(m.group(1))
        if qtd is not None:
            un = m.group(2).upper().replace("LTS", "L")
            return {
                "produto": m.group(3).strip(),
                "quantidade": qtd,
                "unidade": un,
            }
    return None


def parse_insumos_operacao(linhas, extras_txt=""):
    """Linhas = lista de (produto, qtd_txt, unidade). Retorna itens estruturados."""
    itens = []
    for prod, qtd_txt, un in linhas:
        prod = str(prod or "").strip()
        qtd = parse_qtd_insumo(qtd_txt)
        if prod and qtd is not None and un and un != "—":
            itens.append({
                "produto": prod,
                "quantidade": qtd,
                "unidade": str(un).upper().replace("LTS", "L"),
            })
    ext = str(extras_txt or "").strip()
    if ext:
        for parte in re.split(r"[|;\n]+", ext):
            item = _parse_item_insumo(parte)
            if item:
                itens.append(item)
    return itens


def _operacao_valida(nome):
    return bool(nome) and nome not in ("—", "— Selecione —")


def operacao_preenchida(op):
    """True se o bloco de operação tem algum dado relevante."""
    if _operacao_valida(op.get("operacao")):
        return True
    for k in ("talhoes", "local", "inicio_operacao", "fim_operacao"):
        if str(op.get(k) or "").strip():
            return True
    if op.get("h_ini_op", 0) > 0 or op.get("h_fim_op", 0) > 0:
        return True
    return bool(op.get("insumos"))


def montar_resumo_pai(operacoes):
    """Agrega campos flat em apontamento_campo a partir das operações."""
    ops = [o for o in operacoes if operacao_preenchida(o)]
    if not ops:
        return {}
    succoes = [o["operacao"] for o in ops if o.get("operacao")]
    talhoes = [o["talhoes"] for o in ops if o.get("talhoes")]
    locais = [o["local"] for o in ops if o.get("local")]
    inicios = [o["inicio_operacao"] for o in ops if o.get("inicio_operacao")]
    fins = [o["fim_operacao"] for o in ops if o.get("fim_operacao")]

    todos_insumos = []
    qtd_pri, un_pri = None, None
    for o in ops:
        for it in o.get("insumos") or []:
            todos_insumos.append(f"{it['produto']} {it['quantidade']:g} {it['unidade']}")
        if o.get("insumos") and qtd_pri is None:
            it0 = o["insumos"][0]
            qtd_pri = it0["quantidade"]
            un_pri = it0["unidade"]

    succao_res = succoes[0] if len(set(succoes)) == 1 else (succoes[0] if succoes else None)
    if len(set(succoes)) > 1:
        succao_res = succoes[0]

    return {
        "succao": succao_res,
        "talhoes": " | ".join(talhoes) if talhoes else None,
        "local": locais[0] if locais else None,
        "inicio_operacao": min(inicios) if inicios else None,
        "fim_operacao": max(fins) if fins else None,
        "insumo": " | ".join(todos_insumos) if todos_insumos else None,
        "quantidade_insumo": qtd_pri,
        "unidade": un_pri,
    }


def validar_operacoes(operacoes, exige_local=True):
    """Valida lista de operações. Retorna lista de mensagens de erro."""
    ops = [o for o in operacoes if operacao_preenchida(o)]
    erros = []
    if not ops:
        erros.append("Informe ao menos uma operação.")
        return erros
    for i, op in enumerate(ops, 1):
        if not _operacao_valida(op.get("operacao")):
            erros.append(f"Operação {i}: selecione o tipo de operação.")
        if exige_local and not op.get("talhoes") and not op.get("local"):
            erros.append(f"Operação {i}: informe talhão ou local.")
        for lbl, val, raw in [
            ("Início operação", op.get("inicio_operacao"), op.get("_raw_inicio")),
            ("Fim operação", op.get("fim_operacao"), op.get("_raw_fim")),
        ]:
            if str(raw or "").strip() and not val:
                erros.append(f"Operação {i} — {lbl}: use HH:MM (ex: 08:20).")
        h_ini = op.get("h_ini_op") or 0
        h_fim = op.get("h_fim_op") or 0
        if h_fim > 0 and h_ini > 0 and h_fim <= h_ini:
            erros.append(f"Operação {i}: horímetro final deve ser maior que o inicial.")
        if op.get("insumos") and not _operacao_valida(op.get("operacao")):
            erros.append(f"Operação {i}: insumo informado — selecione a operação.")
    return erros


MAX_OPERACOES = 8
MAX_INSUMOS_POR_OP = 5


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


@st.cache_data(ttl=300)
def _mapa_talhoes():
    try:
        res = supabase.table("dim_talhoes").select("id,codigo").eq("ativo", True).execute()
        return {
            str(r["codigo"]).strip(): r["id"]
            for r in (res.data or [])
            if r.get("codigo")
        }
    except Exception:
        return {}


@st.cache_data(ttl=300)
def _mapa_locais():
    try:
        res = supabase.table("dim_locais").select("id,nome").eq("ativo", True).execute()
        out = {}
        for r in res.data or []:
            chave = str(r.get("nome") or "").strip().upper()
            if chave:
                out[chave] = r["id"]
        return out
    except Exception:
        return {}


def resolver_talhao_id(talhoes_txt):
    """Tenta FK em dim_talhoes a partir do código numérico no texto."""
    txt = str(talhoes_txt or "").upper()
    mapa = _mapa_talhoes()
    for cod in re.findall(r"\b(\d{2,4})\b", txt):
        if cod in mapa:
            return mapa[cod]
    return None


def resolver_retiro_id(local_txt, talhoes_txt):
    """Tenta FK em dim_locais pelo local complementar ou texto do talhão."""
    mapa = _mapa_locais()
    for fonte in (local_txt, talhoes_txt):
        txt = str(fonte or "").upper()
        if not txt:
            continue
        for nome, lid in mapa.items():
            if nome in txt:
                return lid
    return None


def gravar_fato_insumos(
    id_apontamento,
    operacao,
    talhoes,
    local,
    inicio_operacao,
    fim_operacao,
    h_inicial,
    h_final,
    itens_insumo,
):
    """Grava fato_operacoes + fato_aplicacao_insumos. Retorna (id_operacao, qtd_insumos)."""
    op_row = {
        "id_apontamento": id_apontamento,
        "operacao": operacao,
        "talhao_id": resolver_talhao_id(talhoes),
        "retiro_id": resolver_retiro_id(local, talhoes),
        "inicio_operacao": inicio_operacao,
        "fim_operacao": fim_operacao,
        "horimetro_inicial_operacao": h_inicial if h_inicial > 0 else None,
        "horimetro_final_operacao": h_final if h_final > 0 else None,
    }
    res_op = supabase.table("fato_operacoes").insert(op_row).execute()
    id_operacao = res_op.data[0]["id"]
    rows = [
        {
            "id_operacao": id_operacao,
            "produto": it["produto"],
            "quantidade": it["quantidade"],
            "unidade": it["unidade"],
        }
        for it in itens_insumo
    ]
    supabase.table("fato_aplicacao_insumos").insert(rows).execute()
    return id_operacao, len(rows)


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
OPERACOES_FORM = ["— Selecione —"] + OPERACOES

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

    if "num_operacoes" not in st.session_state:
        st.session_state.num_operacoes = 1

    b1, b2, b3 = st.columns([1.2, 1.2, 4])
    with b1:
        if st.button("➕ Adicionar operação", key="btn_add_op"):
            if st.session_state.num_operacoes < MAX_OPERACOES:
                st.session_state.num_operacoes += 1
                st.rerun()
    with b2:
        if st.button("➖ Remover operação", key="btn_rem_op"):
            if st.session_state.num_operacoes > 1:
                st.session_state.num_operacoes -= 1
                st.rerun()
    with b3:
        st.caption(
            f"**{st.session_state.num_operacoes}** operação(ões) neste turno — "
            "use ➕ para casos como Josivaldo (548 + 550 no mesmo dia)."
        )

    with st.form("form_apontamento", clear_on_submit=True):
        st.markdown("**Identificação do turno**")
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

        st.markdown("**Horários do turno**")
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            inicio_turno = st.text_input("▶ Início turno", placeholder="06:36")
        with t2:
            fim_turno = st.text_input("⏹ Fim turno", placeholder="18:23")
        with t3:
            almoco = st.text_input("🍽 Almoço (saída)", placeholder="11:42")
        with t4:
            retorno = st.text_input("↩ Retorno", placeholder="13:00")

        st.markdown("**Horímetro do turno**")
        h1, h2, h3 = st.columns(3)
        with h1:
            h_inicial = st.number_input(
                "Horímetro inicial (turno)", min_value=0.0, step=0.1, format="%.1f"
            )
        with h2:
            h_final = st.number_input(
                "Horímetro final (turno)", min_value=0.0, step=0.1, format="%.1f"
            )
        with h3:
            horas = round(h_final - h_inicial, 1)
            if horas > 0:
                st.metric("Horas (horímetro turno)", f"{horas:.1f} h")
            elif h_final > 0 and horas <= 0:
                st.warning("Horímetro final menor que inicial.")

        operacoes_form = []
        for idx in range(st.session_state.num_operacoes):
            st.markdown(f"---")
            st.markdown(f"**Operação {idx + 1}**")
            c_op1, c_op2 = st.columns(2)
            with c_op1:
                succao = st.selectbox(
                    "⚙️ Operação",
                    options=OPERACOES_FORM,
                    key=f"op_{idx}_succao",
                )
            with c_op2:
                talhoes = st.text_input(
                    "🌾 Talhão / área",
                    placeholder="Ex: pasto 548 (deixe vazio se não houver)",
                    key=f"op_{idx}_talhoes",
                )
            local = st.text_input(
                "📍 Local / retiro (opcional)",
                placeholder="Ex: Córrego do Campo",
                key=f"op_{idx}_local",
            )

            o1, o2, o3, o4 = st.columns(4)
            with o1:
                inicio_operacao = st.text_input(
                    "▶ Início operação", placeholder="08:00", key=f"op_{idx}_ini_op"
                )
            with o2:
                fim_operacao = st.text_input(
                    "⏹ Fim operação", placeholder="10:43", key=f"op_{idx}_fim_op"
                )
            with o3:
                h_ini_op = st.number_input(
                    "HR ini. operação",
                    min_value=0.0,
                    step=0.1,
                    format="%.1f",
                    key=f"op_{idx}_h_ini",
                )
            with o4:
                h_fim_op = st.number_input(
                    "HR fim operação",
                    min_value=0.0,
                    step=0.1,
                    format="%.1f",
                    key=f"op_{idx}_h_fim",
                )

            with st.expander(
                f"🧪 Insumos — operação {idx + 1} (opcional)",
                expanded=False,
            ):
                st.caption(
                    "Preencha quando houve aplicação neste talhão/operação. "
                    + OPERACOES_SEM_INSUMO_HINT
                    + " Sem insumo → nada vai para fato_operacoes."
                )
                linhas_insumo = []
                for j in range(MAX_INSUMOS_POR_OP):
                    ic1, ic2, ic3 = st.columns([2, 1, 1])
                    with ic1:
                        prod = st.text_input(
                            f"Produto {j + 1}",
                            placeholder="Ex: Fipronil, Fordor, Calda",
                            key=f"op_{idx}_ins_{j}_prod",
                        )
                    with ic2:
                        qtd = st.text_input(
                            "Qtd",
                            placeholder="0.150",
                            key=f"op_{idx}_ins_{j}_qtd",
                        )
                    with ic3:
                        un = st.selectbox(
                            "Un.",
                            options=UNIDADES_INSUMO,
                            key=f"op_{idx}_ins_{j}_un",
                        )
                    linhas_insumo.append((prod, qtd, un))
                insumos_extras = st.text_area(
                    "Outros (texto livre)",
                    placeholder="Ex: 300 lts calda",
                    key=f"op_{idx}_ins_extras",
                )

            operacoes_form.append({
                "idx": idx,
                "operacao": succao,
                "talhoes": talhoes,
                "local": local,
                "inicio_operacao_raw": inicio_operacao,
                "fim_operacao_raw": fim_operacao,
                "h_ini_op": h_ini_op,
                "h_fim_op": h_fim_op,
                "linhas_insumo": linhas_insumo,
                "insumos_extras": insumos_extras,
            })

        obs = st.text_area("📝 Observação geral")
        submitted = st.form_submit_button(
            "✅ Registrar Apontamento", use_container_width=True, type="primary"
        )

    if submitted:
        hi_turno = parse_hora_txt(inicio_turno)
        hf_turno = parse_hora_txt(fim_turno)
        hi_almoco = parse_hora_txt(almoco)
        hi_retorno = parse_hora_txt(retorno)

        operacoes = []
        for raw in operacoes_form:
            hi_op = parse_hora_txt(raw["inicio_operacao_raw"])
            hf_op = parse_hora_txt(raw["fim_operacao_raw"])
            insumos = parse_insumos_operacao(
                raw["linhas_insumo"], raw["insumos_extras"]
            )
            operacoes.append({
                "operacao": raw["operacao"] if _operacao_valida(raw["operacao"]) else None,
                "talhoes": nulo_se_vazio(
                    raw["talhoes"].strip().upper() if raw["talhoes"] else ""
                ),
                "local": nulo_se_vazio(
                    raw["local"].strip().upper() if raw["local"] else ""
                ),
                "inicio_operacao": hi_op,
                "fim_operacao": hf_op,
                "_raw_inicio": raw["inicio_operacao_raw"],
                "_raw_fim": raw["fim_operacao_raw"],
                "h_ini_op": raw["h_ini_op"],
                "h_fim_op": raw["h_fim_op"],
                "insumos": insumos,
            })

        erros = []
        if not frota.strip():
            erros.append("Informe a frota.")
        if h_final <= h_inicial:
            erros.append("Horímetro final do turno deve ser maior que o inicial.")
        for lbl, val, raw in [
            ("Início turno", hi_turno, inicio_turno),
            ("Fim turno", hf_turno, fim_turno),
            ("Almoço", hi_almoco, almoco),
            ("Retorno", hi_retorno, retorno),
        ]:
            if str(raw or "").strip() and not val:
                erros.append(f"{lbl}: use HH:MM (ex: 08:20).")
        erros.extend(validar_operacoes(operacoes, exige_local=False))

        ops_ativas = [o for o in operacoes if operacao_preenchida(o)]

        if erros:
            for e in erros:
                st.error(f"⚠️ {e}")
        else:
            resumo = montar_resumo_pai(operacoes)
            novo = {
                "data": str(data_ap),
                "operador": operador,
                "frota": frota.strip().upper(),
                "h_inicial": h_inicial,
                "h_final": h_final,
                "succao": resumo.get("succao"),
                "talhoes": resumo.get("talhoes"),
                "local": resumo.get("local"),
                "inicio_turno": hi_turno,
                "fim_turno": hf_turno,
                "inicio_operacao": resumo.get("inicio_operacao"),
                "fim_operacao": resumo.get("fim_operacao"),
                "insumo": resumo.get("insumo"),
                "quantidade_insumo": resumo.get("quantidade_insumo"),
                "unidade": resumo.get("unidade"),
                "observacao": montar_observacao(obs, hi_almoco, hi_retorno),
            }
            try:
                res_ap = supabase.table("apontamento_campo").insert(novo).execute()
                id_apontamento = res_ap.data[0]["id"]

                ops_com_insumo = [
                    o for o in ops_ativas if o.get("insumos")
                ]
                detalhes_fato = []
                for op in ops_com_insumo:
                    id_operacao, n_ins = gravar_fato_insumos(
                        id_apontamento,
                        op["operacao"],
                        op.get("talhoes") or "",
                        op.get("local") or "",
                        op.get("inicio_operacao"),
                        op.get("fim_operacao"),
                        op.get("h_ini_op") or 0,
                        op.get("h_fim_op") or 0,
                        op["insumos"],
                    )
                    tal = op.get("talhoes") or "—"
                    detalhes_fato.append(f"#{id_operacao} ({tal}, {n_ins} ins.)")

                msg_extra = ""
                if detalhes_fato:
                    msg_extra = f" | fato_operacoes: {', '.join(detalhes_fato)}"

                st.success(
                    f"✅ Apontamento #{id_apontamento} salvo! "
                    f"{frota.upper()} | {operador} | {horas:.1f}h | "
                    f"{len(ops_ativas)} op(s){msg_extra}"
                )
                st.session_state.num_operacoes = 1
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
