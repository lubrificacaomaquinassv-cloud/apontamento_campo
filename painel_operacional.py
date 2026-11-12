# -*- coding: utf-8 -*-
"""Painel operacional de campo — só leitura. Sem inserção, sem sidebar, sem OS oficina."""
from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import html
from datetime import date
from io import BytesIO

import altair as alt
import pandas as pd
import streamlit as st
from supabase import create_client

try:
    from pwa_medidas import carregar_medidas, datas_disponiveis, fmt_br, fmt_moeda
except ImportError:
    import importlib

    import pwa_medidas as _pwa_medidas

    importlib.reload(_pwa_medidas)
    carregar_medidas = _pwa_medidas.carregar_medidas
    datas_disponiveis = _pwa_medidas.datas_disponiveis
    fmt_br = _pwa_medidas.fmt_br
    fmt_moeda = _pwa_medidas.fmt_moeda
from sigcf_auth import exigir_acesso, logo_html
from sigcf_theme import dark_table, inject_theme, render_footer, render_header

st.set_page_config(
    page_title="Painel operacional — SIGCF",
    page_icon="assets/logo_santa_verginia.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

exigir_acesso("Painel operacional de campo")

PAINEL_CSS = """
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"]{
 display:none!important;width:0!important;min-width:0!important;}
.main .block-container{max-width:1320px;}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:4px 0 18px;}
@media (max-width:900px){.kpi-grid{grid-template-columns:repeat(2,1fr);}}
.kpi-card{
 background:var(--sigcf-card);border:1px solid var(--sigcf-border);
 border-radius:12px;padding:14px 16px;box-shadow:var(--sigcf-shadow-md);}
.kpi-op{border-left:4px solid var(--sigcf-green);}
.kpi-clima{border-left:4px solid #5eb3ff;}
.kpi-mec{border-left:4px solid #ff8a65;}
.kpi-des{border-left:4px solid var(--sigcf-ouro);}
.kpi-fuel{border-left:4px solid var(--sigcf-gold);}
.kpi-mo{border-left:4px solid #e8b84a;border-color:var(--sigcf-ouro);}
.kpi-lbl{
 font-size:11px;color:var(--sigcf-label);letter-spacing:.12em;
 text-transform:uppercase;font-weight:600;margin:0 0 6px;}
.kpi-val{
 font-size:1.7rem;color:var(--sigcf-gold);font-weight:700;
 font-variant-numeric:tabular-nums;line-height:1.1;margin:0;}
.kpi-hint{font-size:11px;color:var(--sigcf-label);margin:8px 0 0;letter-spacing:.04em;}
.comp-wrap{margin:8px 0 18px;}
.comp-meta{
 display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
 font-size:11px;color:var(--sigcf-label);letter-spacing:.08em;
 text-transform:uppercase;margin-bottom:8px;}
.comp-bar{display:flex;height:18px;border-radius:9px;overflow:hidden;
 background:#1a2818;border:1px solid var(--sigcf-border);}
.comp-bar span{display:block;height:100%;}
.comp-leg{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;font-size:11px;
 color:var(--sigcf-text);letter-spacing:.06em;text-transform:uppercase;}
.comp-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;
 vertical-align:middle;}
.nota-oficina{
 background:var(--sigcf-card);border:1px solid var(--sigcf-border);
 border-left:4px solid var(--sigcf-ouro);border-radius:12px;
 padding:12px 16px;margin:0 0 18px;font-size:13px;color:var(--sigcf-text);}
.nota-oficina strong{color:var(--sigcf-gold);letter-spacing:.08em;text-transform:uppercase;
 font-size:12px;}
.filtros-box{
 background:var(--sigcf-card);border:1px solid var(--sigcf-border);
 border-radius:12px;padding:8px 12px 4px;margin-bottom:16px;}
"""
inject_theme(PAINEL_CSS)

render_header(
    logo_html,
    "Painel operacional de campo",
    "SIGCF — leitura dos lançamentos PWA · horímetro, paradas, deslocamento e combustível",
)

def _cliente():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


@st.cache_data(ttl=90)
def _medidas_cache(d_ini: str, d_fim: str, frotas: tuple[str, ...], ops: tuple[str, ...]):
    return carregar_medidas(
        _cliente(),
        date.fromisoformat(d_ini),
        date.fromisoformat(d_fim),
        list(frotas) or None,
        list(ops) or None,
    )


def _kpi(cls: str, label: str, valor: str, hint: str) -> str:
    return (
        f'<div class="kpi-card {cls}">'
        f'<div class="kpi-lbl">{html.escape(label)}</div>'
        f'<div class="kpi-val">{html.escape(valor)}</div>'
        f'<div class="kpi-hint">{html.escape(hint)}</div></div>'
    )


def _excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _altair_base(chart):
    return (
        chart.configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            labelColor="#e8edd0",
            titleColor="#8aab80",
            gridColor="#2a4030",
            domainColor="#2a4030",
        )
        .configure_legend(labelColor="#e8edd0", titleColor="#8aab80")
    )


try:
    dmin, dmax = datas_disponiveis(_cliente())
except Exception:
    st.error("Sem conexão com o Supabase. Confira internet e o arquivo .streamlit/secrets.toml.")
    st.stop()

st.markdown('<div class="filtros-box">', unsafe_allow_html=True)
f1, f2, f3 = st.columns([1.3, 1.5, 1.4])
with f1:
    periodo = st.date_input(
        "Período",
        value=(dmin, dmax),
        min_value=dmin,
        max_value=dmax,
    )
    recarregar = st.button("Atualizar")

if recarregar:
    st.cache_data.clear()

if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
    d_ini, d_fim = periodo
else:
    d_ini = d_fim = periodo

_bruto_pre = _medidas_cache(str(d_ini), str(d_fim), tuple(), tuple())
df_turnos_pre = _bruto_pre.get("turnos")
if isinstance(df_turnos_pre, pd.DataFrame) and not df_turnos_pre.empty:
    frotas_all = sorted(df_turnos_pre["frota"].dropna().astype(str).unique())
    ops_all = sorted(df_turnos_pre["operador"].dropna().astype(str).unique())
else:
    frotas_all, ops_all = [], []

with f2:
    frotas_sel = st.multiselect("Frota", frotas_all, default=frotas_all)
with f3:
    ops_sel = st.multiselect("Operador", ops_all, default=[])
st.markdown("</div>", unsafe_allow_html=True)

med = _medidas_cache(
    str(d_ini),
    str(d_fim),
    tuple(frotas_sel),
    tuple(ops_sel),
)
k = med["kpis"]

st.markdown(
    '<div class="nota-oficina"><strong>Oficina (OS)</strong> — fora deste painel. '
    "O setor ainda não lança ordem de serviço por falta de internet. "
    "Parada mecânica aqui é só o evento do PWA no talhão, não tempo de OS.</div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="kpi-grid">'
    + _kpi(
        "kpi-op",
        "Hora operada",
        fmt_br(k["hora_operada"], 1, " h"),
        f"{k['n_hr_ok']} turnos com horímetro válido de {k['n_encerrado']} encerrados",
    )
    + _kpi(
        "kpi-clima",
        "Parada por clima",
        fmt_br(k["h_clima"], 1, " h"),
        f"{k['n_clima']} eventos fechados no período",
    )
    + _kpi(
        "kpi-mec",
        "Parada mecânica",
        fmt_br(k["h_mecanica"], 1, " h"),
        f"{k['n_mecanica']} eventos · sem OS de oficina",
    )
    + _kpi(
        "kpi-des",
        "Deslocamentos",
        fmt_br(k["h_desloc"], 1, " h"),
        f"{k['n_desloc']} lançamentos com saída e chegada",
    )
    + "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="kpi-grid">'
    + _kpi(
        "kpi-fuel",
        "Diesel comboio",
        fmt_br(k["litros_comboio"], 0, " L"),
        "Tabela comboio_v2",
    )
    + _kpi(
        "kpi-fuel",
        "Diesel posto",
        fmt_br(k["litros_posto"], 0, " L"),
        "Tabela posto",
    )
    + _kpi(
        "kpi-op",
        "Diesel total",
        fmt_br(k["litros_total"], 0, " L"),
        "Mesmas frotas do apontamento",
    )
    + _kpi(
        "kpi-op",
        "Consumo médio",
        fmt_br(k["l_por_hora"], 1, " L/h") if k["l_por_hora"] is not None else "—",
        "Litros ÷ hora operada válida",
    )
    + "</div>",
    unsafe_allow_html=True,
)

_mo_val = k.get("custo_mo_total")
_mo_hint = (
    f"{k.get('n_turnos_custo', 0)} turnos com salário · média "
    f"{fmt_moeda(k.get('custo_hora_medio'))}/h operada"
    if _mo_val is not None
    else "Sem custo/hora — sincronize Controladoria_10_Máquinas.xls"
)
st.markdown(
    '<div class="kpi-grid" style="grid-template-columns:repeat(2,1fr);max-width:640px;">'
    + _kpi(
        "kpi-mo",
        "Custo mão de obra",
        fmt_moeda(_mo_val) if _mo_val is not None else "—",
        _mo_hint,
    )
    + _kpi(
        "kpi-op",
        "Salário base",
        "Controladoria + dim_colaborador",
        "Bruto ÷ 220 h · sem encargos · snapshot nov/2026",
    )
    + "</div>",
    unsafe_allow_html=True,
)

if k["n_aberto"]:
    st.info(f"{k['n_aberto']} turno(s) ainda aberto(s) — não entram na hora operada.")

total_comp = (
    k["h_operada_relogio"] + k["h_almoco"] + k["h_mecanica"] + k["h_clima"] + k["h_desloc"]
)
if total_comp > 0:
    segs = [
        ("operada", k["h_operada_relogio"], "#6fcf60", "Operada (relógio)"),
        ("almoco", k["h_almoco"], "#5a6b58", "Almoço"),
        ("mec", k["h_mecanica"], "#ff8a65", "Mecânica"),
        ("clima", k["h_clima"], "#5eb3ff", "Clima"),
        ("des", k["h_desloc"], "#c9a227", "Deslocamento"),
    ]
    barras = "".join(
        f'<span style="width:{(v / total_comp) * 100:.2f}%;background:{cor};" title="{lab}: {fmt_br(v, 1)} h"></span>'
        for _, v, cor, lab in segs
        if v > 0
    )
    leg = "".join(
        f'<span><i class="comp-dot" style="background:{cor}"></i>{html.escape(lab)} {fmt_br(v, 1)} h</span>'
        for _, v, cor, lab in segs
    )
    st.markdown('<div class="sec">Composição da jornada (relógio)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="comp-wrap"><div class="comp-meta">'
        f"<span>Intervalos classificados {fmt_br(total_comp, 1)} h</span>"
        f"<span>Horímetro {fmt_br(k['hora_operada'], 1)} h</span>"
        f"</div><div class=\"comp-bar\">{barras}</div>"
        f'<div class="comp-leg">{leg}</div></div>',
        unsafe_allow_html=True,
    )

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="sec">Horas por tipo</div>', unsafe_allow_html=True)
    df_tipo = pd.DataFrame(
        {
            "tipo": ["Operada (relógio)", "Almoço", "Mecânica", "Deslocamento", "Clima"],
            "horas": [
                k["h_operada_relogio"],
                k["h_almoco"],
                k["h_mecanica"],
                k["h_desloc"],
                k["h_clima"],
            ],
        }
    )
    chart_h = (
        alt.Chart(df_tipo)
        .mark_bar(size=36, cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "tipo:N",
                sort=["Operada (relógio)", "Almoço", "Mecânica", "Deslocamento", "Clima"],
                title=None,
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y("horas:Q", title="Horas"),
            color=alt.Color(
                "tipo:N",
                legend=None,
                scale=alt.Scale(
                    domain=["Operada (relógio)", "Almoço", "Mecânica", "Deslocamento", "Clima"],
                    range=["#6fcf60", "#5a6b58", "#ff8a65", "#c9a227", "#5eb3ff"],
                ),
            ),
            tooltip=["tipo", "horas"],
        )
        .properties(height=260)
    )
    st.altair_chart(_altair_base(chart_h), width="stretch")

with c2:
    st.markdown('<div class="sec">Diesel por frota</div>', unsafe_allow_html=True)
    df_f = med["frota"]
    if df_f.empty:
        st.info("Sem abastecimento cruzado neste filtro.")
    else:
        df_fuel = df_f[["frota", "litros_comboio", "litros_posto"]].melt(
            id_vars=["frota"],
            value_vars=["litros_comboio", "litros_posto"],
            var_name="fonte",
            value_name="qtd_litros",
        )
        df_fuel["fonte"] = df_fuel["fonte"].map(
            {"litros_comboio": "Comboio", "litros_posto": "Posto"}
        )
        ordem = df_f.sort_values("litros", ascending=False)["frota"].tolist()
        chart_l = (
            alt.Chart(df_fuel)
            .mark_bar()
            .encode(
                x=alt.X("frota:N", sort=ordem, title="Frota"),
                y=alt.Y("qtd_litros:Q", title="Litros", stack="zero"),
                color=alt.Color(
                    "fonte:N",
                    scale=alt.Scale(domain=["Comboio", "Posto"], range=["#6fcf60", "#ffd966"]),
                    legend=alt.Legend(title=None, orient="top"),
                ),
                tooltip=["frota", "fonte", "qtd_litros"],
            )
            .properties(height=260)
        )
        st.altair_chart(_altair_base(chart_l), width="stretch")

st.markdown('<div class="sec">Leitura por frota</div>', unsafe_allow_html=True)
if df_f.empty:
    st.info("Nenhum turno no período.")
else:
    mostra = df_f[
        [
            "frota",
            "turnos",
            "hora_operada",
            "l_por_hora",
            "litros",
            "litros_comboio",
            "litros_posto",
            "h_clima",
            "h_mecanica",
            "h_desloc",
        ]
    ].copy()
    mostra["hora_operada"] = mostra["hora_operada"].map(lambda v: fmt_br(v, 1))
    mostra["h_clima"] = mostra["h_clima"].map(lambda v: fmt_br(v, 1))
    mostra["h_mecanica"] = mostra["h_mecanica"].map(lambda v: fmt_br(v, 1))
    mostra["h_desloc"] = mostra["h_desloc"].map(lambda v: fmt_br(v, 1))
    mostra["litros_comboio"] = mostra["litros_comboio"].map(lambda v: fmt_br(v, 0))
    mostra["litros_posto"] = mostra["litros_posto"].map(lambda v: fmt_br(v, 0))
    mostra["litros"] = mostra["litros"].map(lambda v: fmt_br(v, 0))
    mostra["l_por_hora"] = mostra["l_por_hora"].map(
        lambda v: fmt_br(v, 1) if v is not None else "—"
    )
    mostra = mostra.rename(
        columns={
            "frota": "Frota",
            "turnos": "Turnos",
            "hora_operada": "Hora operada",
            "l_por_hora": "L/h",
            "litros": "Diesel (L)",
            "litros_comboio": "Comboio (L)",
            "litros_posto": "Posto (L)",
            "h_clima": "Clima",
            "h_mecanica": "Mecânica",
            "h_desloc": "Desloc.",
        }
    )
    dark_table(mostra, height=420)
    st.download_button(
        "Exportar Excel",
        data=_excel(df_f),
        file_name=f"painel_campo_{d_ini}_{d_fim}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

inv = med["invalidos"]
if not inv.empty:
    st.markdown('<div class="sec">Horímetro fora da hora operada</div>', unsafe_allow_html=True)
    inv_m = inv.copy()
    inv_m["data"] = pd.to_datetime(inv_m["data"], errors="coerce").dt.strftime("%d/%m/%Y")
    for col in ("hori", "horf"):
        inv_m[col] = inv_m[col].apply(
            lambda v: "—" if v is None or (isinstance(v, float) and pd.isna(v)) else v
        )
    inv_m = inv_m.rename(
        columns={
            "id_turno": "ID",
            "data": "Data",
            "frota": "Frota",
            "operador": "Operador",
            "hori": "HORI",
            "horf": "HORF",
            "hr_invalido": "Motivo",
        }
    )
    dark_table(inv_m, height=220)

fonte = med.get("fonte", "python")
render_footer(
    "SIGCF | Painel operacional de campo | Núcleo de Controladoria SV · "
    f"fonte: {fonte} (vw_api_campo_* / PostgREST)"
)
