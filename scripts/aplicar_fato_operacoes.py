#!/usr/bin/env python3
"""Aplica 006_fato_operacoes_insumos.sql no Supabase."""
import sys
import tomllib
from pathlib import Path
import psycopg2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "sql" / "006_fato_operacoes_insumos.sql").read_text(encoding="utf-8")
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"
cfg = tomllib.load(open(SECRETS, "rb"))["connections"]["supabase"]
conn = psycopg2.connect(
    host=cfg["host"],
    port=cfg["port"],
    database=cfg["database"],
    user=cfg["username"],
    password=cfg["password"],
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()

buf = []
for line in SQL.splitlines():
    s = line.strip()
    if not s or s.startswith("--"):
        continue
    buf.append(line)
    if ";" in line:
        stmt = "\n".join(buf).strip()
        if stmt.endswith(";"):
            stmt = stmt[:-1].strip()
        if stmt:
            cur.execute(stmt)
            preview = stmt.replace("\n", " ")[:100]
            print("OK:", preview)
        buf = []

cur.execute(
    """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('fato_operacoes', 'fato_aplicacao_insumos')
    ORDER BY 1
    """
)
print("\n=== Tabelas criadas ===")
for r in cur.fetchall():
    print(r[0])

for tbl in ("fato_operacoes", "fato_aplicacao_insumos"):
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (tbl,),
    )
    print(f"\n=== {tbl} ===")
    for r in cur.fetchall():
        print(f"  {r[0]:30} {r[1]}")

cur.execute(
    "SELECT count(*) FROM information_schema.views "
    "WHERE table_schema = 'public' AND table_name = 'vw_aplicacao_insumos_campo'"
)
print("\nvw_aplicacao_insumos_campo:", "OK" if cur.fetchone()[0] else "AUSENTE")

conn.close()
print("\nConcluido.")
