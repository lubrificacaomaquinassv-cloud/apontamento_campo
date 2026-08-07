#!/usr/bin/env python3
"""Aplica 004_sap_retiros_talhoes.sql"""
import tomllib
from pathlib import Path
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "sql" / "004_sap_retiros_talhoes.sql").read_text(encoding="utf-8")
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"
cfg = tomllib.load(open(SECRETS, "rb"))["connections"]["supabase"]
conn = psycopg2.connect(
    host=cfg["host"], port=cfg["port"], database=cfg["database"],
    user=cfg["username"], password=cfg["password"], sslmode="require",
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
            print("OK:", stmt.replace("\n", " ")[:85])
        buf = []

cur.execute("SELECT ordem_sap, regra_distribuicao, retiro FROM vw_retiros_sap ORDER BY ordem_sap")
print("\n=== vw_retiros_sap (ordem SAP) ===")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT * FROM vw_talhoes_sap")
print("\n=== vw_talhoes_sap ===")
for r in cur.fetchall():
    print(r)

conn.close()
print("\nConcluido.")
