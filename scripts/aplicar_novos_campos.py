#!/usr/bin/env python3
"""Aplica migration 002_novos_campos_apontamento.sql no Supabase."""
import tomllib
from pathlib import Path
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
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

cur.execute(
    """
    ALTER TABLE public.apontamento_campo
      ADD COLUMN IF NOT EXISTS inicio_turno       time,
      ADD COLUMN IF NOT EXISTS fim_turno          time,
      ADD COLUMN IF NOT EXISTS inicio_operacao    time,
      ADD COLUMN IF NOT EXISTS fim_operacao       time,
      ADD COLUMN IF NOT EXISTS talhoes            text,
      ADD COLUMN IF NOT EXISTS insumo             text,
      ADD COLUMN IF NOT EXISTS quantidade_insumo  numeric(12, 4),
      ADD COLUMN IF NOT EXISTS unidade            text
    """
)
print("ALTER TABLE OK")

cur.execute(
    """
    SELECT column_name FROM information_schema.columns
    WHERE table_schema='public' AND table_name='apontamento_campo'
      AND column_name IN ('inicio_turno','fim_turno','inicio_operacao','fim_operacao',
                          'talhoes','insumo','quantidade_insumo','unidade')
    ORDER BY 1
    """
)
print("Colunas novas:", [r[0] for r in cur.fetchall()])
conn.close()
