# -*- coding: utf-8 -*-
"""Medidas do painel operacional — calculadas na leitura, não gravadas nas tabelas.

Quando as views vw_api_campo_* existirem, este módulo passa a lê-las
em vez de recomputar. A fórmula deve permanecer a mesma.
"""
from __future__ import annotations

__all__ = [
    "carregar_medidas",
    "carregar_medidas_api",
    "carregar_bruto",
    "montar_medidas",
    "datas_disponiveis",
    "fmt_br",
    "fmt_moeda",
]

import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pandas as pd

HORIMETRO_MAX_H = 16.0
PAGE = 1000

# Próximo evento que fecha cada parada (relógio). Sem virada de dia:
# lançamento de campo é diurno; hora invertida é erro de seq, não overnight.
FECHA_CLIMA = {"RETORNO_OPERACAO", "FIM_OPERACAO", "FINALIZAR_TALHAO"}
FECHA_MEC = {"RETORNO_OPERACAO"}
FECHA_ALMOCO = {"RETORNO_ALMOCO"}

TRABALHO_INI = {"INICIO_OPERACAO", "RETORNO_ALMOCO", "RETORNO_OPERACAO"}
TRABALHO_FIM = {
    "PARADA_ALMOCO",
    "PARADA_CLIMA",
    "PARADA_MECANICA",
    "PARADA_PREPARO_INSUMOS",
    "FIM_OPERACAO",
    "FINALIZAR_TALHAO",
    "FINAL_TURNO",
}


def fmt_moeda(v, casas=2) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_br(v, casas=1, sufixo="") -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s}{sufixo}"


def hora_operada_horimetro(hori, horf):
    """HORF − HORI só se 0 ≤ delta ≤ 16. Retorna (horas, motivo_invalido)."""
    if hori is None or horf is None:
        return None, "sem HORF" if hori is not None else "sem HORI"
    try:
        dlt = float(horf) - float(hori)
    except (TypeError, ValueError):
        return None, "horímetro ilegível"
    if dlt < 0:
        return None, "HORF menor que HORI"
    if dlt > HORIMETRO_MAX_H:
        return None, f"delta {dlt:.1f} h acima de {HORIMETRO_MAX_H:.0f} h"
    return round(dlt, 2), None


def _minutos(v) -> int | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, time):
        return v.hour * 60 + v.minute
    if isinstance(v, datetime):
        return v.hour * 60 + v.minute
    s = str(v).strip()
    if not s or s in ("None", "NaT"):
        return None
    partes = s.replace(".", ":").split(":")
    try:
        return int(partes[0]) * 60 + int(partes[1])
    except (TypeError, ValueError, IndexError):
        return None


def delta_horas_relogio(ini, fim) -> float | None:
    a, b = _minutos(ini), _minutos(fim)
    if a is None or b is None:
        return None
    d = b - a
    if d < 0 or d / 60.0 > HORIMETRO_MAX_H:
        return None
    return round(d / 60.0, 2)


def _fetch_paged(sb, table: str, select: str, apply=None) -> list[dict]:
    out: list[dict] = []
    start = 0
    while True:
        q = sb.table(table).select(select)
        if apply:
            q = apply(q)
        res = q.range(start, start + PAGE - 1).execute()
        batch = res.data or []
        out.extend(batch)
        if len(batch) < PAGE:
            break
        start += PAGE
    return out


def _fetch_in(sb, table: str, select: str, col: str, ids: list, extra=None) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(ids), 80):
        chunk = ids[i : i + 80]

        def apply(q, _chunk=chunk):
            q = q.in_(col, _chunk)
            if extra:
                q = extra(q)
            return q

        out.extend(_fetch_paged(sb, table, select, apply))
    return out


def _pares_turno(eventos: list[dict]) -> dict:
    evs = sorted(eventos, key=lambda e: (e.get("seq") or 0, str(e.get("hora") or "")))
    clima = mec = almoco = operada_rel = 0.0
    n_clima = n_mec = n_almoco = 0
    n_clima_ab = n_mec_ab = 0

    for i, ev in enumerate(evs):
        if i + 1 >= len(evs):
            cod = ev.get("codigo_evento") or ""
            if cod == "PARADA_CLIMA":
                n_clima_ab += 1
            elif cod == "PARADA_MECANICA":
                n_mec_ab += 1
            continue
        nxt = evs[i + 1]
        dur = delta_horas_relogio(ev.get("hora"), nxt.get("hora"))
        if dur is None:
            continue
        cod = ev.get("codigo_evento") or ""
        ncod = nxt.get("codigo_evento") or ""

        if cod == "PARADA_CLIMA" and ncod in FECHA_CLIMA:
            clima += dur
            n_clima += 1
        elif cod == "PARADA_MECANICA" and ncod in FECHA_MEC:
            mec += dur
            n_mec += 1
        elif cod == "PARADA_ALMOCO" and ncod in FECHA_ALMOCO:
            almoco += dur
            n_almoco += 1
        elif (
            cod in TRABALHO_INI
            and ncod in TRABALHO_FIM
            and not (cod == "RETORNO_OPERACAO" and ncod == "RETORNO_OPERACAO")
        ):
            operada_rel += dur

    return {
        "h_clima": round(clima, 2),
        "h_mecanica": round(mec, 2),
        "h_almoco": round(almoco, 2),
        "h_operada_relogio": round(operada_rel, 2),
        "n_clima": n_clima,
        "n_mecanica": n_mec,
        "n_almoco": n_almoco,
        "n_clima_aberto": n_clima_ab,
        "n_mecanica_aberto": n_mec_ab,
    }


def _desloc_turno(rows: list[dict]) -> dict:
    h_rel = h_hr = 0.0
    n = 0
    for r in rows:
        d_rel = delta_horas_relogio(r.get("hora_saida"), r.get("hora_chegada"))
        if d_rel is not None:
            h_rel += d_rel
            n += 1
        hs, hc = r.get("horimetro_saida"), r.get("horimetro_chegada")
        if hs is not None and hc is not None:
            try:
                dhr = float(hc) - float(hs)
            except (TypeError, ValueError):
                dhr = None
            if dhr is not None and 0 <= dhr <= HORIMETRO_MAX_H:
                h_hr += dhr
    return {
        "h_desloc": round(h_rel, 2),
        "h_desloc_hr": round(h_hr, 2),
        "n_desloc": n,
    }


def _diesel(combustivel: str) -> bool:
    c = str(combustivel or "").upper()
    return "DIESEL" in c or c in ("S10", "S500", "S-10", "S-500")


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (datetime, date, time)):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def carregar_bruto(sb, d_ini: date, d_fim: date) -> dict:
    """Lê tabelas operacionais. Não altera nada."""
    di, df_ = str(d_ini), str(d_fim)

    def filtro_data(q):
        return q.gte("data", di).lte("data", df_)

    turnos = _fetch_paged(
        sb,
        "campo_turno",
        "id,data,id_frota,operador,operacao_nome,status,"
        "horimetro_inicio_turno,horimetro_fim_turno,"
        "hora_inicio_turno,hora_fim_turno",
        filtro_data,
    )
    turnos = [t for t in turnos if (t.get("status") or "") != "CANCELADO"]
    ids = [int(t["id"]) for t in turnos if t.get("id") is not None]

    eventos = _fetch_in(
        sb,
        "fato_evento_campo",
        "id_turno,seq,codigo_evento,hora,horimetro",
        "id_turno",
        ids,
    ) if ids else []

    desloc = _fetch_in(
        sb,
        "fato_deslocamentos",
        "id_turno,tipo,hora_saida,hora_chegada,horimetro_saida,horimetro_chegada",
        "id_turno",
        ids,
    ) if ids else []

    frotas = sorted({str(t.get("id_frota") or "").strip() for t in turnos if t.get("id_frota")})

    abast: list[dict] = []
    try:

        def filtro_abast(q):
            return q.gte("created_at", f"{di}T00:00:00").lte("created_at", f"{df_}T23:59:59")

        abast = _fetch_paged(
            sb,
            "vw_abastecimento_unificado",
            "created_at,frota,combustivel,litros,fonte",
            filtro_abast,
        )
    except Exception:
        abast = _abast_fallback(sb, d_ini, d_fim)

    return _json_safe(
        {
            "turnos": turnos,
            "eventos": eventos,
            "desloc": desloc,
            "abast": abast,
            "frotas_turno": frotas,
        }
    )


def _abast_fallback(sb, d_ini: date, d_fim: date) -> list[dict]:
    di, df_ = f"{d_ini}T00:00:00", f"{d_fim}T23:59:59"
    out = []
    for table, fonte in (("comboio_v2", "COMBOIO_V2"), ("posto", "POSTO")):
        try:
            rows = _fetch_paged(
                sb,
                table,
                "created_at,vehicle,fuel_type,liters",
                lambda q, _di=di, _df=df_: q.gte("created_at", _di).lte("created_at", _df),
            )
        except Exception:
            continue
        for r in rows:
            out.append(
                {
                    "created_at": r.get("created_at"),
                    "frota": r.get("vehicle"),
                    "combustivel": r.get("fuel_type"),
                    "litros": r.get("liters"),
                    "fonte": fonte,
                }
            )
    return out


def montar_medidas(bruto: dict, frotas_filtro: list[str] | None, operadores: list[str] | None) -> dict:
    ev_por = {}
    for e in bruto["eventos"]:
        ev_por.setdefault(int(e["id_turno"]), []).append(e)
    ds_por = {}
    for d in bruto["desloc"]:
        ds_por.setdefault(int(d["id_turno"]), []).append(d)

    fset = {str(f).strip() for f in (frotas_filtro or []) if str(f).strip()}
    oset = {str(o).strip() for o in (operadores or []) if str(o).strip()}

    linhas = []
    for t in bruto["turnos"]:
        frota = str(t.get("id_frota") or "").strip()
        op = str(t.get("operador") or "").strip()
        if fset and frota not in fset:
            continue
        if oset and op not in oset:
            continue
        tid = int(t["id"])
        h_hr, motivo = hora_operada_horimetro(
            t.get("horimetro_inicio_turno"),
            t.get("horimetro_fim_turno"),
        )
        pares = _pares_turno(ev_por.get(tid, []))
        des = _desloc_turno(ds_por.get(tid, []))
        linhas.append(
            {
                "id_turno": tid,
                "data": t.get("data"),
                "frota": frota,
                "operador": op,
                "operacao": (t.get("operacao_nome") or "").strip(),
                "status": t.get("status"),
                "hori": t.get("horimetro_inicio_turno"),
                "horf": t.get("horimetro_fim_turno"),
                "hora_operada_hr": h_hr if t.get("status") == "ENCERRADO" else None,
                "hr_invalido": motivo if t.get("status") == "ENCERRADO" else (
                    "turno aberto" if t.get("status") == "ABERTO" else None
                ),
                **pares,
                **des,
            }
        )

    df = pd.DataFrame(linhas)
    if df.empty:
        return _vazio()

    frotas_ok = sorted(df["frota"].dropna().unique())
    abast_rows = []
    for r in bruto["abast"]:
        fr = str(r.get("frota") or "").strip()
        if frotas_ok and fr not in frotas_ok:
            continue
        if not _diesel(r.get("combustivel")):
            continue
        try:
            lit = float(r.get("litros") or 0)
        except (TypeError, ValueError):
            lit = 0.0
        if lit <= 0:
            continue
        fonte = str(r.get("fonte") or "").upper()
        if "POSTO" in fonte:
            origem = "POSTO"
        else:
            origem = "COMBOIO"
        abast_rows.append({"frota": fr, "litros": lit, "fonte": origem})
    df_ab = pd.DataFrame(abast_rows)

    enc = df[df["status"] == "ENCERRADO"]
    hora_op = float(enc["hora_operada_hr"].fillna(0).sum())
    h_clima = float(df["h_clima"].fillna(0).sum())
    h_mec = float(df["h_mecanica"].fillna(0).sum())
    h_des = float(df["h_desloc"].fillna(0).sum())
    h_alm = float(df["h_almoco"].fillna(0).sum())
    h_rel = float(df["h_operada_relogio"].fillna(0).sum())

    lit_comboio = float(df_ab.loc[df_ab["fonte"] == "COMBOIO", "litros"].sum()) if not df_ab.empty else 0.0
    lit_posto = float(df_ab.loc[df_ab["fonte"] == "POSTO", "litros"].sum()) if not df_ab.empty else 0.0
    lit_total = lit_comboio + lit_posto
    lph = round(lit_total / hora_op, 1) if hora_op > 0 and lit_total > 0 else None

    g_hr = enc.groupby("frota", dropna=False)["hora_operada_hr"].sum(min_count=1)
    g_n = df.groupby("frota").size()
    g_cl = df.groupby("frota")["h_clima"].sum()
    g_mc = df.groupby("frota")["h_mecanica"].sum()
    g_ds = df.groupby("frota")["h_desloc"].sum()

    if df_ab.empty:
        g_co = pd.Series(dtype=float)
        g_po = pd.Series(dtype=float)
    else:
        g_co = df_ab[df_ab["fonte"] == "COMBOIO"].groupby("frota")["litros"].sum()
        g_po = df_ab[df_ab["fonte"] == "POSTO"].groupby("frota")["litros"].sum()

    frota_idx = sorted(set(g_n.index) | set(g_co.index) | set(g_po.index))
    frota_rows = []
    for fr in frota_idx:
        hr = float(g_hr.get(fr, 0) or 0)
        lc = float(g_co.get(fr, 0) or 0)
        lp = float(g_po.get(fr, 0) or 0)
        lt = lc + lp
        frota_rows.append(
            {
                "frota": fr,
                "turnos": int(g_n.get(fr, 0) or 0),
                "hora_operada": round(hr, 1),
                "h_clima": round(float(g_cl.get(fr, 0) or 0), 1),
                "h_mecanica": round(float(g_mc.get(fr, 0) or 0), 1),
                "h_desloc": round(float(g_ds.get(fr, 0) or 0), 1),
                "litros_comboio": round(lc, 0),
                "litros_posto": round(lp, 0),
                "litros": round(lt, 0),
                "l_por_hora": round(lt / hr, 1) if hr > 0 and lt > 0 else None,
            }
        )
    df_frota = pd.DataFrame(frota_rows).sort_values("hora_operada", ascending=False)

    invalidos = enc[enc["hora_operada_hr"].isna()][
        ["id_turno", "data", "frota", "operador", "hori", "horf", "hr_invalido"]
    ].copy()

    return {
        "turnos": df,
        "frota": df_frota,
        "invalidos": invalidos,
        "abast": df_ab,
        "kpis": {
            "hora_operada": round(hora_op, 1),
            "n_hr_ok": int(enc["hora_operada_hr"].notna().sum()),
            "n_encerrado": int(len(enc)),
            "n_aberto": int((df["status"] == "ABERTO").sum()),
            "n_frotas": int(df["frota"].nunique()),
            "h_clima": round(h_clima, 1),
            "n_clima": int(df["n_clima"].sum()),
            "h_mecanica": round(h_mec, 1),
            "n_mecanica": int(df["n_mecanica"].sum()),
            "h_desloc": round(h_des, 1),
            "n_desloc": int(df["n_desloc"].sum()),
            "h_almoco": round(h_alm, 1),
            "h_operada_relogio": round(h_rel, 1),
            "litros_comboio": round(lit_comboio, 0),
            "litros_posto": round(lit_posto, 0),
            "litros_total": round(lit_total, 0),
            "l_por_hora": lph,
        },
    }


def _vazio() -> dict:
    return {
        "turnos": pd.DataFrame(),
        "frota": pd.DataFrame(),
        "invalidos": pd.DataFrame(),
        "abast": pd.DataFrame(),
        "kpis": {
            "hora_operada": 0,
            "n_hr_ok": 0,
            "n_encerrado": 0,
            "n_aberto": 0,
            "n_frotas": 0,
            "h_clima": 0,
            "n_clima": 0,
            "h_mecanica": 0,
            "n_mecanica": 0,
            "h_desloc": 0,
            "n_desloc": 0,
            "h_almoco": 0,
            "h_operada_relogio": 0,
            "litros_comboio": 0,
            "litros_posto": 0,
            "litros_total": 0,
            "l_por_hora": None,
            "custo_mo_total": None,
            "n_turnos_custo": 0,
            "custo_hora_medio": None,
        },
    }


def _custo_mo_turnos(sb, turnos_df: pd.DataFrame) -> dict:
    """Soma custo MO (hora operada × custo/h) a partir da view de turno."""
    if turnos_df.empty:
        return {"custo_mo_total": None, "n_turnos_custo": 0, "custo_hora_medio": None}
    try:
        custos = _fetch_paged(
            sb,
            "vw_api_custo_hora_pwa",
            "operador_key,operador,custo_hora,fonte_salario",
        )
    except Exception:
        return {"custo_mo_total": None, "n_turnos_custo": 0, "custo_hora_medio": None}
    if not custos:
        return {"custo_mo_total": None, "n_turnos_custo": 0, "custo_hora_medio": None}

    def _key(op):
        return re.sub(r"\s+", " ", str(op or "").strip().upper())

    mapa = {_key(r.get("operador")): float(r["custo_hora"]) for r in custos if r.get("custo_hora")}
    total = 0.0
    n = 0
    enc = turnos_df[turnos_df["status"] == "ENCERRADO"] if "status" in turnos_df.columns else turnos_df
    for _, row in enc.iterrows():
        h = row.get("hora_operada_hr")
        if h is None or (isinstance(h, float) and pd.isna(h)):
            continue
        try:
            horas = float(h)
        except (TypeError, ValueError):
            continue
        if horas <= 0:
            continue
        ch = mapa.get(_key(row.get("operador")))
        if ch is None or ch <= 0:
            continue
        total += horas * ch
        n += 1
    hora_op = float(enc["hora_operada_hr"].fillna(0).sum()) if "hora_operada_hr" in enc.columns else 0.0
    media = round(total / hora_op, 2) if hora_op > 0 and total > 0 else None
    return {
        "custo_mo_total": round(total, 2) if total > 0 else None,
        "n_turnos_custo": n,
        "custo_hora_medio": media,
    }


def _aplica_filtros_turno(row: dict, fset: set[str], oset: set[str]) -> bool:
    fr = str(row.get("frota") or "").strip()
    op = str(row.get("operador") or "").strip()
    if fset and fr not in fset:
        return False
    if oset and op not in oset:
        return False
    return True


def carregar_medidas_api(
    sb,
    d_ini: date,
    d_fim: date,
    frotas_filtro: list[str] | None = None,
    operadores: list[str] | None = None,
) -> dict | None:
    """Lê views vw_api_campo_* no Supabase. Retorna None se a view ainda não existir."""
    di, df_ = str(d_ini), str(d_fim)
    fset = {str(f).strip() for f in (frotas_filtro or []) if str(f).strip()}
    oset = {str(o).strip() for o in (operadores or []) if str(o).strip()}

    try:

        def filtro_data(q):
            return q.gte("data", di).lte("data", df_)

        turnos_raw = _fetch_paged(sb, "vw_api_campo_turno_medidas", "*", filtro_data)
        fd_raw = _fetch_paged(sb, "vw_api_campo_frota_dia", "*", filtro_data)
        abast_dia = _fetch_paged(sb, "vw_api_campo_abast_dia_frota", "*", filtro_data)
    except Exception:
        return None

    if not turnos_raw:
        return _vazio()

    turnos_raw = [t for t in turnos_raw if _aplica_filtros_turno(t, fset, oset)]
    if fset:
        fd_raw = [r for r in fd_raw if str(r.get("frota") or "").strip() in fset]

    df = pd.DataFrame(turnos_raw)
    if df.empty:
        return _vazio()

    if "hora_operada_hr" not in df.columns:
        return None

    enc = df[df["status"] == "ENCERRADO"]
    hora_op = float(enc["hora_operada_hr"].fillna(0).sum())
    h_clima = float(df["h_clima"].fillna(0).sum())
    h_mec = float(df["h_mecanica"].fillna(0).sum())
    h_des = float(df["h_desloc"].fillna(0).sum())
    h_alm = float(df["h_almoco"].fillna(0).sum())
    h_rel = float(df["h_operada_relogio"].fillna(0).sum())
    n_clima = int(df.get("n_clima", pd.Series([0])).fillna(0).sum())
    n_mec = int(df.get("n_mecanica", pd.Series([0])).fillna(0).sum())
    n_des = int(df.get("n_desloc", pd.Series([0])).fillna(0).sum())

    fd = pd.DataFrame(fd_raw) if fd_raw else pd.DataFrame()
    adf = pd.DataFrame(abast_dia) if abast_dia else pd.DataFrame()
    frotas_ok = set(df["frota"].dropna().astype(str).unique())
    if fset:
        frotas_ok &= fset
    if not adf.empty and frotas_ok:
        adf = adf[adf["frota"].astype(str).isin(frotas_ok)]

    lit_comboio = lit_posto = lit_total = 0.0
    df_frota = pd.DataFrame()
    if not adf.empty:
        lit_comboio = float(adf["litros_comboio"].fillna(0).sum())
        lit_posto = float(adf["litros_posto"].fillna(0).sum())
        lit_total = float(adf["litros_total"].fillna(0).sum())

    if not fd.empty:
        g = fd.groupby("frota", dropna=False).agg(
            turnos=("n_turnos", "sum"),
            hora_operada=("hora_operada_hr", "sum"),
            h_clima=("h_clima", "sum"),
            h_mecanica=("h_mecanica", "sum"),
            h_desloc=("h_desloc", "sum"),
        )
        g["hora_operada"] = g["hora_operada"].round(1)
        for c in ("h_clima", "h_mecanica", "h_desloc"):
            g[c] = g[c].round(1)
        if not adf.empty:
            gf = adf.groupby("frota", dropna=False).agg(
                litros_comboio=("litros_comboio", "sum"),
                litros_posto=("litros_posto", "sum"),
                litros=("litros_total", "sum"),
            )
            g = g.join(gf, how="outer")
        else:
            g["litros_comboio"] = 0
            g["litros_posto"] = 0
            g["litros"] = 0
        g["turnos"] = g["turnos"].fillna(0)
        g["hora_operada"] = g["hora_operada"].fillna(0).round(1)
        for c in ("h_clima", "h_mecanica", "h_desloc"):
            g[c] = g[c].fillna(0).round(1)
        for c in ("litros_comboio", "litros_posto", "litros"):
            g[c] = g[c].fillna(0).round(0)
        g["l_por_hora"] = g.apply(
            lambda r: round(r["litros"] / r["hora_operada"], 1)
            if r["hora_operada"] > 0 and r["litros"] > 0
            else None,
            axis=1,
        )
        df_frota = g.reset_index().sort_values("hora_operada", ascending=False)
    else:
        g_hr = enc.groupby("frota", dropna=False)["hora_operada_hr"].sum(min_count=1)
        g_n = df.groupby("frota").size()
        g_cl = df.groupby("frota")["h_clima"].sum()
        g_mc = df.groupby("frota")["h_mecanica"].sum()
        g_ds = df.groupby("frota")["h_desloc"].sum()
        frota_rows = []
        for fr in sorted(g_n.index):
            hr = float(g_hr.get(fr, 0) or 0)
            frota_rows.append(
                {
                    "frota": fr,
                    "turnos": int(g_n.get(fr, 0)),
                    "hora_operada": round(hr, 1),
                    "h_clima": round(float(g_cl.get(fr, 0) or 0), 1),
                    "h_mecanica": round(float(g_mc.get(fr, 0) or 0), 1),
                    "h_desloc": round(float(g_ds.get(fr, 0) or 0), 1),
                    "litros_comboio": 0,
                    "litros_posto": 0,
                    "litros": 0,
                    "l_por_hora": None,
                }
            )
        df_frota = pd.DataFrame(frota_rows)

    lph = round(lit_total / hora_op, 1) if hora_op > 0 and lit_total > 0 else None
    invalidos = enc[enc["hora_operada_hr"].isna()][
        ["id_turno", "data", "frota", "operador", "hori", "horf", "hr_invalido"]
    ].copy()

    mo = _custo_mo_turnos(sb, df)

    return {
        "turnos": df,
        "frota": df_frota,
        "invalidos": invalidos,
        "abast": pd.DataFrame(),
        "fonte": "api",
        "kpis": {
            "hora_operada": round(hora_op, 1),
            "n_hr_ok": int(enc["hora_operada_hr"].notna().sum()),
            "n_encerrado": int(len(enc)),
            "n_aberto": int((df["status"] == "ABERTO").sum()),
            "n_frotas": int(df["frota"].nunique()),
            "h_clima": round(h_clima, 1),
            "n_clima": n_clima,
            "h_mecanica": round(h_mec, 1),
            "n_mecanica": n_mec,
            "h_desloc": round(h_des, 1),
            "n_desloc": n_des,
            "h_almoco": round(h_alm, 1),
            "h_operada_relogio": round(h_rel, 1),
            "litros_comboio": round(lit_comboio, 0),
            "litros_posto": round(lit_posto, 0),
            "litros_total": round(lit_total, 0),
            "l_por_hora": lph,
            **mo,
        },
    }


def carregar_medidas(
    sb,
    d_ini: date,
    d_fim: date,
    frotas_filtro: list[str] | None = None,
    operadores: list[str] | None = None,
) -> dict:
    """Preferência: views API; fallback: cálculo Python nas tabelas."""
    api = carregar_medidas_api(sb, d_ini, d_fim, frotas_filtro, operadores)
    if api is not None:
        return api
    bruto = carregar_bruto(sb, d_ini, d_fim)
    out = montar_medidas(bruto, frotas_filtro, operadores)
    out["fonte"] = "python"
    if isinstance(out.get("turnos"), pd.DataFrame):
        out["kpis"].update(_custo_mo_turnos(sb, out["turnos"]))
    return out


def datas_disponiveis(sb) -> tuple[date, date]:
    try:
        rmin = (
            sb.table("campo_turno")
            .select("data")
            .neq("status", "CANCELADO")
            .order("data")
            .limit(1)
            .execute()
        )
        rmax = (
            sb.table("campo_turno")
            .select("data")
            .neq("status", "CANCELADO")
            .order("data", desc=True)
            .limit(1)
            .execute()
        )
        dmin = date.fromisoformat(str((rmin.data or [{}])[0].get("data")))
        dmax = date.fromisoformat(str((rmax.data or [{}])[0].get("data")))
        return dmin, dmax
    except Exception:
        hoje = date.today()
        return hoje - timedelta(days=30), hoje
