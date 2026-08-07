#!/usr/bin/env python3
"""
Le PDFs em D:\\APOSTILA 2026 IMPRIMIR, valida talhoes x retiro e atualiza dim_talhoes.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import fitz
import psycopg2
from psycopg2.extras import execute_batch

APOSTILA_DIR = Path(r"D:\APOSTILA 2026 IMPRIMIR")
SECRETS = Path(__file__).resolve().parents[2] / "requisicao-compras" / ".streamlit" / "secrets.toml"

REGRAS_AREA: list[tuple[str, str, str | None]] = [
    (r"C\s*C\s*\+\s*A\s*B|CORREGO\s*DO\s*CAMPO|CÓRREGO\s*DO\s*CAMPO", "RETIRO CORREGO DO CAMPO", "RETIRO 4"),
    (r"TAQUARUSSU", "RETIRO TAQUARUSSU", "RETIRO 5"),
    (r"BARRA\s*DO\s*CERVO", "RETIRO BARRA DO CERVO", "RETIRO 6"),
    (r"POCO\s*AZUL|POÇO\s*AZUL", "RETIRO POÇO AZUL", "RETIRO1"),
    (r"AGUA\s*BRANCA|ÁGUA\s*BRANCA", "RETIRO ÁGUA BRANCA", "RETIRO2"),
    (r"EUCALIPTO", "RETIRO EUCALIPTO", "RETIRO3"),
    (r"TIP.*SEDE|^SEDE", "RETIRO SEDE", "RETIRO"),
    (r"ALDEIA", "ALDEIA", None),
    (r"^TIP", "TIP", None),
    (r"JUREMA", "JUREMA", None),
]

SPEC_SEM_TALHAO = {"MATRIZ", "DENSO", "LAJEADO", "CITRIODORA"}


def sem_acento(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii").upper().strip()


def sort_code(c: str):
    m = re.match(r"^(\d+)([A-Z]?)$", c)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, c, "")


def parse_filename(pdf: Path) -> tuple[str, str, str]:
    stem = pdf.stem.strip()
    m = re.match(r"^(\d{4})\s+(.+?)\s*\(([^)]+)\)\s*$", stem)
    if m:
        return m.group(1), m.group(2).strip(), m.group(3).strip()
    m2 = re.match(r"^(\d+)\s*-\s*(.+)$", stem)
    if m2:
        return "", m2.group(2).strip(), ""
    return "", stem, ""


def match_area(area_bruta: str) -> tuple[str, str | None] | None:
    norm = sem_acento(area_bruta)
    for pat, loc_nome, sap in REGRAS_AREA:
        if re.search(pat, norm, re.I):
            return loc_nome, sap
    return None


MAX_FAIXA_AUTO = 50  # faixas maiores dependem do PDF ou apostila combinada


def parse_spec_talhoes(spec: str) -> set[str]:
    spec = spec.strip()
    if not spec or spec.upper() in SPEC_SEM_TALHAO:
        return set()

    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", spec)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        span = b - a + 1
        if b >= a:
            # Faixa curta ou numeracao alta de talhao (>=200)
            if span <= MAX_FAIXA_AUTO or (a >= 200 and span <= 150):
                return {str(i) for i in range(a, b + 1)}
        return set()

    out: set[str] = set()
    for part in re.split(r"[-–,;]+", spec):
        part = part.strip().upper()
        if not part:
            continue
        sub = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if sub:
            a, b = int(sub.group(1)), int(sub.group(2))
            span = b - a + 1
            if b >= a and (span <= MAX_FAIXA_AUTO or (a >= 200 and span <= 150)):
                out.update(str(i) for i in range(a, b + 1))
            continue
        if re.fullmatch(r"\d+[A-Z]?", part):
            out.add(part)
    return out


def extract_talhoes_pdf_text(text: str, valid_codes: set[str]) -> set[str]:
    """Extrai codigos que aparecem sozinhos em linha (padrao das apostilas)."""
    found: set[str] = set()
    for line in text.splitlines():
        token = line.strip().upper()
        if re.fullmatch(r"\d{1,3}[A-Z]?", token) and token in valid_codes:
            found.add(token)
    return found


def pdf_priority(r: "PdfResult") -> tuple[int, int, str]:
    """Maior = mais especifico (vence conflitos)."""
    combined = 1 if "C C" in sem_acento(r.area) or "+" in r.area else 0
    has_spec = 1 if len(r.talhoes_spec) >= 3 else 0
    try:
        ano = int(r.ano) if r.ano else 0
    except ValueError:
        ano = 0
    return (has_spec, -combined, ano, r.arquivo)


@dataclass
class PdfResult:
    arquivo: str
    ano: str
    area: str
    local_nome: str | None
    codigo_sap: str | None
    spec_arquivo: str
    talhoes_spec: set[str] = field(default_factory=set)
    talhoes_pdf: set[str] = field(default_factory=set)
    talhoes_final: set[str] = field(default_factory=set)
    avisos: list[str] = field(default_factory=list)


def process_pdfs(valid_codes: set[str]) -> list[PdfResult]:
    results: list[PdfResult] = []
    for pdf in sorted(APOSTILA_DIR.glob("*.pdf")):
        if pdf.name.startswith("~$"):
            continue
        ano, area, spec = parse_filename(pdf)
        if "PROJETOS FLORESTAIS" in sem_acento(area):
            continue
        match = match_area(area)
        r = PdfResult(
            arquivo=pdf.name,
            ano=ano,
            area=area,
            local_nome=match[0] if match else None,
            codigo_sap=match[1] if match else None,
            spec_arquivo=spec,
        )
        if not match:
            r.avisos.append(f"Area nao mapeada: {area}")

        r.talhoes_spec = parse_spec_talhoes(spec)
        try:
            doc = fitz.open(pdf)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            r.talhoes_pdf = extract_talhoes_pdf_text(text, valid_codes)
        except Exception as e:
            r.avisos.append(f"Erro leitura PDF: {e}")

        if r.talhoes_spec:
            r.talhoes_final = set(r.talhoes_spec)
            if r.talhoes_pdf:
                r.talhoes_final |= r.talhoes_pdf
                missing = r.talhoes_spec - r.talhoes_pdf
                extra = r.talhoes_pdf - r.talhoes_spec
                if missing:
                    r.avisos.append(f"Spec sem linha no PDF ({len(missing)}): {sorted(missing, key=sort_code)[:12]}")
                if extra and len(extra) <= 15:
                    r.avisos.append(f"PDF alem da spec ({len(extra)}): {sorted(extra, key=sort_code)[:12]}")
        else:
            r.talhoes_final = r.talhoes_pdf

        results.append(r)
    return results


def build_talhao_retiro(results: list[PdfResult]) -> tuple[dict[str, dict], list[str]]:
    """Atribui talhao ao PDF mais especifico em caso de conflito."""
    candidates: dict[str, list[dict]] = {}
    for r in results:
        if not r.local_nome or not r.talhoes_final:
            continue
        pri = pdf_priority(r)
        for cod in r.talhoes_final:
            entry = {
                "local_nome": r.local_nome,
                "codigo_sap": r.codigo_sap,
                "fonte": r.arquivo,
                "priority": pri,
            }
            candidates.setdefault(cod, []).append(entry)

    mapping: dict[str, dict] = {}
    conflitos: list[str] = []
    for cod, opts in candidates.items():
        opts.sort(key=lambda x: x["priority"], reverse=True)
        best = opts[0]
        for other in opts[1:]:
            if other["local_nome"] != best["local_nome"]:
                conflitos.append(
                    f"{cod}: {best['local_nome']} ({best['fonte']}) <- descartado {other['local_nome']} ({other['fonte']})"
                )
        mapping[cod] = {
            "local_nome": best["local_nome"],
            "codigo_sap": best["codigo_sap"],
            "fonte": best["fonte"],
        }
    return mapping, conflitos


def load_dim_locais(cur) -> dict[str, int]:
    cur.execute("SELECT id, nome, codigo_sap FROM dim_locais WHERE ativo = true")
    by_key: dict[str, int] = {}
    for id_, nome, sap in cur.fetchall():
        by_key[sem_acento(nome)] = id_
        if sap:
            by_key[sem_acento(sap)] = id_
    aliases = {
        "RETIRO1": by_key.get(sem_acento("RETIRO POÇO AZUL")),
        "RETIRO2": by_key.get(sem_acento("RETIRO ÁGUA BRANCA")),
        "RETIRO3": by_key.get(sem_acento("RETIRO EUCALIPTO")),
        "RETIRO 4": by_key.get(sem_acento("RETIRO CORREGO DO CAMPO")),
        "RETIRO 5": by_key.get(sem_acento("RETIRO TAQUARUSSU")),
        "RETIRO 6": by_key.get(sem_acento("RETIRO BARRA DO CERVO")),
        "RETIRO": by_key.get(sem_acento("RETIRO SEDE")),
    }
    for k, v in aliases.items():
        if v:
            by_key[k] = v
    return by_key


def ensure_jurema_local(cur, loc_index: dict[str, int], dry_run: bool) -> None:
    if sem_acento("JUREMA") in loc_index:
        return
    if dry_run:
        print("DRY-RUN: criaria dim_locais JUREMA (LOCALIDADE)")
        return
    cur.execute(
        """
        INSERT INTO dim_locais (nome, tipo, tipo_operacional, cidade, uf, pais, ativo)
        VALUES ('JUREMA', 'INTERNO', 'LOCALIDADE', 'Bataguassu', 'MS', 'Brasil', true)
        ON CONFLICT DO NOTHING
        """
    )
    cur.execute("SELECT id FROM dim_locais WHERE upper(trim(nome)) = 'JUREMA' AND ativo = true")
    row = cur.fetchone()
    if row:
        loc_index[sem_acento("JUREMA")] = row[0]


def resolve_id_local(local_nome: str, codigo_sap: str | None, loc_index: dict[str, int]) -> int | None:
    for key in (local_nome, codigo_sap or ""):
        if key and sem_acento(key) in loc_index:
            return loc_index[sem_acento(key)]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="So valida, nao grava no banco")
    args = parser.parse_args()

    if not APOSTILA_DIR.is_dir():
        print(f"ERRO: pasta nao encontrada: {APOSTILA_DIR}")
        sys.exit(1)

    cfg = tomllib.load(open(SECRETS, "rb"))["connections"]["supabase"]
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["username"], password=cfg["password"], sslmode="require",
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT codigo FROM dim_talhoes WHERE ativo = true")
    valid_codes = {str(r[0]).upper() for r in cur.fetchall()}

    results = process_pdfs(valid_codes)
    mapping, conflitos = build_talhao_retiro(results)
    loc_index = load_dim_locais(cur)
    ensure_jurema_local(cur, loc_index, args.dry_run)
    if not args.dry_run:
        loc_index = load_dim_locais(cur)

    print("=" * 70)
    print(" VALIDACAO — APOSTILA 2026 IMPRIMIR")
    print("=" * 70)
    print(f"PDFs processados: {len(results)}")
    print(f"Talhoes unicos mapeados: {len(mapping)}")
    print(f"Conflitos resolvidos (log): {len(conflitos)}")

    for r in results:
        if not r.talhoes_final and not r.avisos:
            continue
        print(f"\n--- {r.arquivo} ---")
        print(f"  Local: {r.local_nome or '?'} | SAP: {r.codigo_sap or '-'}")
        print(f"  Talhoes: {len(r.talhoes_final)} (spec:{len(r.talhoes_spec)} pdf-linhas:{len(r.talhoes_pdf)})")
        for av in r.avisos:
            print(f"  AVISO: {av}")

    if conflitos:
        print(f"\n--- Conflitos resolvidos ({min(15, len(conflitos))} de {len(conflitos)}) ---")
        for c in conflitos[:15]:
            print(f"  {c}")

    updates = []
    inserts = []
    sem_local = []
    nao_cadastrados = []
    for cod, info in sorted(mapping.items(), key=lambda x: sort_code(x[0])):
        id_local = resolve_id_local(info["local_nome"], info["codigo_sap"], loc_index)
        if cod not in valid_codes:
            nao_cadastrados.append(cod)
            if id_local:
                inserts.append({
                    "codigo": cod,
                    "nome": f"TALHAO {cod}",
                    "id_local": id_local,
                    "codigo_sap_retiro": info["codigo_sap"],
                    "observacao": f"Cadastro apostila PDF: {info['fonte']}",
                })
            else:
                sem_local.append((cod, info["local_nome"]))
            continue
        if not id_local:
            sem_local.append((cod, info["local_nome"]))
            continue
        updates.append({
            "codigo": cod,
            "id_local": id_local,
            "codigo_sap_retiro": info["codigo_sap"],
            "obs_suffix": f"Retiro apostila: {info['fonte']}",
        })

    print("\n--- Resumo cadastro ---")
    print(f"  Atualizar com retiro: {len(updates)}")
    print(f"  Inserir novo talhao (so apostila): {len(inserts)}")
    print(f"  Codigo na apostila sem dim_talhoes/local: {len(nao_cadastrados) - len(inserts)}")
    print(f"  Sem dim_locais: {len(sem_local)}")
    if sem_local[:8]:
        print(f"  Ex.: {sem_local[:8]}")

    # Amostra de conferencia
    checks = ["547", "464", "410", "201B", "105A"]
    print("\n--- Amostra ---")
    for c in checks:
        if c in mapping:
            print(f"  {c} -> {mapping[c]['local_nome']} ({mapping[c]['fonte']})")

    if args.dry_run:
        print("\nDRY-RUN: nenhuma alteracao gravada.")
        conn.rollback()
        conn.close()
        return

    if updates:
        execute_batch(
            cur,
            """
            UPDATE dim_talhoes SET
              id_local = %(id_local)s,
              codigo_sap_retiro = %(codigo_sap_retiro)s,
              observacao = trim(both E'\\n' from concat(
                coalesce(observacao, ''), E'\\n', %(obs_suffix)s
              ))
            WHERE upper(trim(codigo)) = upper(trim(%(codigo)s))
            """,
            updates,
            page_size=200,
        )

    if inserts:
        execute_batch(
            cur,
            """
            INSERT INTO dim_talhoes (codigo, nome, id_local, codigo_sap_retiro, observacao, ativo)
            SELECT %(codigo)s, %(nome)s, %(id_local)s, %(codigo_sap_retiro)s, %(observacao)s, true
            WHERE NOT EXISTS (
              SELECT 1 FROM dim_talhoes t
              WHERE upper(trim(t.codigo)) = upper(trim(%(codigo)s))
            )
            """,
            inserts,
            page_size=200,
        )

    conn.commit()

    cur.execute("SELECT count(*) FROM dim_talhoes WHERE id_local IS NOT NULL")
    com_ret = cur.fetchone()[0]
    cur.execute(
        """
        SELECT l.nome, l.codigo_sap, count(*)
        FROM dim_talhoes t
        JOIN dim_locais l ON l.id = t.id_local
        GROUP BY l.nome, l.codigo_sap, l.ordem_sap
        ORDER BY l.ordem_sap NULLS LAST, count(*) DESC
        """
    )
    print(f"\ndim_talhoes com retiro vinculado: {com_ret}")
    print("Por retiro:")
    for nome, sap, qtd in cur.fetchall():
        print(f"  {sap or '-':10} {nome}: {qtd}")

    sem = len(valid_codes) - com_ret
    print(f"Sem retiro (KML sem apostila): {sem}")

    conn.close()
    print("\nConcluido.")


if __name__ == "__main__":
    main()
