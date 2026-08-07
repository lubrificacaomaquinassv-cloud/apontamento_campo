#!/usr/bin/env python3
"""
Carrega talhões do KML fazenda_santa_virginia_completo.kml → dim_talhoes (Supabase).
Uso: python carregar_talhoes_kml.py [caminho.kml]
"""
from __future__ import annotations

import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KML = Path(r"d:\fazenda_santa_virginia_completo.kml")
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"


def local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def get_text(parent, tag: str) -> str:
    for c in parent:
        if local(c.tag) == tag:
            return (c.text or "").strip()
    return ""


def parse_desc(desc: str) -> tuple[float | None, str | None]:
    d = desc.replace("&lt;", "<").replace("&gt;", ">").replace("<br/>", "\n")
    area = None
    classe = None
    m = re.search(r"[ÁáAa]rea.*?(\d+\.?\d*)\s*ha", d)
    if m:
        area = float(m.group(1))
    m2 = re.search(r"Classe.*?[:>]\s*([^<\n]+)", d)
    if m2:
        classe = m2.group(1).strip()
    return area, classe


def parse_kml(path: Path) -> dict[str, dict]:
    placemarks: list[dict] = []
    folder_stack: list[str] = []

    for event, elem in ET.iterparse(path, events=("start", "end")):
        tag = local(elem.tag)
        if event == "start" and tag == "Folder":
            folder_stack.append("")
        elif event == "end":
            if tag == "name" and folder_stack:
                folder_stack[-1] = (elem.text or "").strip()
            elif tag == "Placemark":
                placemarks.append(
                    {
                        "name": get_text(elem, "name"),
                        "path": [x for x in folder_stack if x],
                        "area_ha": parse_desc(get_text(elem, "description"))[0],
                        "classe": parse_desc(get_text(elem, "description"))[1],
                    }
                )
                elem.clear()
            elif tag == "Folder":
                if folder_stack:
                    folder_stack.pop()
                elem.clear()

    talhoes: dict[str, dict] = {}
    pat = re.compile(r"^(Silvicultura|Silvipastoril|Pastagem|TIP)\s+(.+)$", re.I)

    def add(codigo, nome, classe, area_ha, fonte, path_str):
        codigo = str(codigo or "").strip()
        if not codigo or codigo.lower() == "nan":
            return
        key = codigo.upper()
        obs = f"KML Santa Virgínia | {fonte}"
        row = {
            "codigo": key,
            "nome": nome or f"TALHÃO {key}",
            "classe_uso": (classe or "").upper() or None,
            "area_ha": area_ha,
            "observacao": obs,
        }
        cur = talhoes.get(key)
        if cur is None:
            talhoes[key] = row
            return
        if area_ha and (cur["area_ha"] is None or area_ha > cur["area_ha"]):
            cur["area_ha"] = area_ha
        if classe and not cur["classe_uso"]:
            cur["classe_uso"] = classe.upper()
        if cur["nome"].startswith("TALHÃO") and nome and not nome.startswith("TALHÃO"):
            cur["nome"] = nome

    for p in placemarks:
        if any("Talh" in x for x in p["path"]):
            idx = next(i for i, x in enumerate(p["path"]) if "Talh" in x)
            rest = p["path"][idx + 1 :]
            codigo = rest[0] if rest else p["name"]
            nome = p["name"] if p["name"] and p["name"].lower() != "nan" else None
            if not nome and p["classe"]:
                nome = f"{p['classe'].upper()} {codigo}"
            add(codigo, nome, p["classe"], p["area_ha"], "Talhões", " > ".join(p["path"][-2:]))

    for p in placemarks:
        if not any("Uso do Solo" in x for x in p["path"]):
            continue
        leaf = p["path"][-1] if p["path"] else p["name"]
        m = pat.match(leaf or "") or (pat.match(p["name"]) if p["name"] else None)
        if m:
            classe, codigo = m.group(1), m.group(2).strip()
            add(codigo, f"{classe.upper()} {codigo}", classe, p["area_ha"], "Uso do Solo", leaf)

    return talhoes


def main():
    kml_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KML
    if not kml_path.is_file():
        print(f"ERRO: KML não encontrado: {kml_path}")
        sys.exit(1)

    talhoes = parse_kml(kml_path)
    print(f"Talhões únicos no KML: {len(talhoes)}")

    cfg = tomllib.load(open(SECRETS, "rb"))["connections"]["supabase"]
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        user=cfg["username"],
        password=cfg["password"],
        sslmode="require",
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(
        """
        ALTER TABLE public.dim_talhoes
          ADD COLUMN IF NOT EXISTS area_ha numeric(10, 4),
          ADD COLUMN IF NOT EXISTS classe_uso text
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_talhoes_codigo
          ON public.dim_talhoes (codigo)
          WHERE codigo IS NOT NULL AND trim(codigo) <> ''
        """
    )

    rows = list(talhoes.values())
    execute_batch(
        cur,
        """
        INSERT INTO dim_talhoes (codigo, nome, classe_uso, area_ha, observacao, ativo)
        VALUES (%(codigo)s, %(nome)s, %(classe_uso)s, %(area_ha)s, %(observacao)s, true)
        ON CONFLICT (codigo) WHERE codigo IS NOT NULL AND trim(codigo) <> ''
        DO UPDATE SET
          nome = EXCLUDED.nome,
          classe_uso = COALESCE(EXCLUDED.classe_uso, dim_talhoes.classe_uso),
          area_ha = COALESCE(EXCLUDED.area_ha, dim_talhoes.area_ha),
          observacao = EXCLUDED.observacao
        """,
        rows,
        page_size=200,
    )

    # Propaga codigo_sap_retiro onde id_local já definido
    cur.execute(
        """
        UPDATE dim_talhoes t SET codigo_sap_retiro = l.codigo_sap
        FROM dim_locais l
        WHERE l.id = t.id_local AND t.codigo_sap_retiro IS DISTINCT FROM l.codigo_sap
        """
    )

    conn.commit()
    cur.execute("SELECT count(*) FROM dim_talhoes WHERE ativo")
    total = cur.fetchone()[0]
    cur.execute(
        "SELECT classe_uso, count(*) FROM dim_talhoes WHERE ativo GROUP BY 1 ORDER BY 2 DESC"
    )
    print(f"Total dim_talhoes ativos: {total}")
    print("Por classe_uso:")
    for r in cur.fetchall():
        print(f"  {r[0] or '(vazio)'}: {r[1]}")
    conn.close()
    print("Carga concluída.")


if __name__ == "__main__":
    main()
