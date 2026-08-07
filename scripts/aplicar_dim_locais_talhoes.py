#!/usr/bin/env python3
"""Aplica 003_dim_locais_talhoes.sql no Supabase."""
import tomllib
from pathlib import Path
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "sql" / "003_dim_locais_talhoes.sql").read_text(encoding="utf-8")
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

# Executa statement a statement (ignora comentários)
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
            preview = stmt.replace("\n", " ")[:90]
            print("OK:", preview)
        buf = []

cur.execute(
    """
    SELECT id, nome, tipo, tipo_operacional
    FROM dim_locais
    WHERE tipo = 'INTERNO' OR tipo_operacional = 'EXTERNO'
    ORDER BY tipo_operacional NULLS LAST, id
    """
)
print("\n=== dim_locais (interno + externo) ===")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT id, codigo, nome, id_local FROM dim_talhoes ORDER BY id")
print("\n=== dim_talhoes ===")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT count(*) FROM vw_localidades_sv WHERE escopo = 'INTERNO'")
print("\nvw_localidades_sv (INTERNO):", cur.fetchone()[0], "registros")

conn.close()
print("\nConcluido.")
