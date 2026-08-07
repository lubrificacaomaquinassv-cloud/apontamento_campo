-- =============================================================================
-- Retiros alinhados ao SAP (regra de distribuição) + dim_talhoes para consumo
-- Ordem de lançamento SAP (consumo por localidade):
--   1 SEDE → RETIRO
--   2 Córrego do Campo → RETIRO 4
--   3 Taquarussu → RETIRO 5
--   4 Barra do Cervo → RETIRO 6
--   5 Poço Azul → RETIRO1
--   6 Água Branca → RETIRO2
--   7 Eucalipto → RETIRO3
-- =============================================================================

ALTER TABLE public.dim_locais
  ADD COLUMN IF NOT EXISTS codigo_sap text,
  ADD COLUMN IF NOT EXISTS ordem_sap smallint;

COMMENT ON COLUMN public.dim_locais.codigo_sap IS
  'Código exato da regra de distribuição SAP (RETIRO, RETIRO1, RETIRO 4, etc.)';
COMMENT ON COLUMN public.dim_locais.ordem_sap IS
  'Ordem de exibição/lançamento SAP para retiros (1–7)';

-- SEDE
UPDATE public.dim_locais SET
  nome = 'RETIRO SEDE',
  tipo_operacional = 'RETIRO',
  codigo_sap = 'RETIRO',
  ordem_sap = 1
WHERE id = 21 OR upper(trim(nome)) IN ('SEDE', 'RETIRO SEDE');

UPDATE public.dim_locais SET nome = 'RETIRO CORREGO DO CAMPO', tipo_operacional = 'RETIRO 4', codigo_sap = 'RETIRO 4', ordem_sap = 2
WHERE id = 5;

UPDATE public.dim_locais SET nome = 'RETIRO TAQUARUSSU', tipo_operacional = 'RETIRO 5', codigo_sap = 'RETIRO 5', ordem_sap = 3
WHERE id = 3;

UPDATE public.dim_locais SET nome = 'RETIRO BARRA DO CERVO', tipo_operacional = 'RETIRO 6', codigo_sap = 'RETIRO 6', ordem_sap = 4
WHERE id = 2;

UPDATE public.dim_locais SET nome = 'RETIRO POÇO AZUL', tipo_operacional = 'RETIRO 1', codigo_sap = 'RETIRO1', ordem_sap = 5
WHERE id = 1;

UPDATE public.dim_locais SET nome = 'RETIRO ÁGUA BRANCA', tipo_operacional = 'RETIRO 2', codigo_sap = 'RETIRO2', ordem_sap = 6
WHERE id = 4;

UPDATE public.dim_locais SET nome = 'RETIRO EUCALIPTO', tipo_operacional = 'RETIRO 3', codigo_sap = 'RETIRO3', ordem_sap = 7
WHERE id = 6;

-- dim_talhoes: garantir estrutura + código SAP do retiro pai
ALTER TABLE public.dim_talhoes
  ADD COLUMN IF NOT EXISTS codigo_sap_retiro text,
  ADD COLUMN IF NOT EXISTS ordem smallint;

COMMENT ON COLUMN public.dim_talhoes.codigo_sap_retiro IS
  'Cópia da regra SAP do retiro (dim_locais.codigo_sap) — facilita lançamento';
COMMENT ON COLUMN public.dim_talhoes.codigo IS
  'Código do talhão/pasto no SAP ou campo (ex.: 547)';

UPDATE public.dim_talhoes t SET
  codigo_sap_retiro = l.codigo_sap
FROM public.dim_locais l
WHERE l.id = t.id_local AND t.codigo_sap_retiro IS DISTINCT FROM l.codigo_sap;

-- View retiros na ordem SAP
CREATE OR REPLACE VIEW public.vw_retiros_sap AS
SELECT
  id,
  ordem_sap,
  codigo_sap AS regra_distribuicao,
  nome AS retiro,
  tipo_operacional,
  cidade,
  uf,
  ativo
FROM public.dim_locais
WHERE codigo_sap IS NOT NULL
  AND ordem_sap IS NOT NULL
ORDER BY ordem_sap;

COMMENT ON VIEW public.vw_retiros_sap IS
  'Retiros na ordem de lançamento SAP — regra de distribuição + nome';

-- View talhões com retiro SAP
CREATE OR REPLACE VIEW public.vw_talhoes_sap AS
SELECT
  t.id,
  t.codigo AS codigo_talhao,
  t.nome AS talhao,
  t.codigo_sap_retiro AS regra_distribuicao,
  l.nome AS retiro,
  l.ordem_sap AS ordem_retiro,
  t.observacao,
  t.ativo
FROM public.dim_talhoes t
JOIN public.dim_locais l ON l.id = t.id_local
WHERE t.ativo
ORDER BY l.ordem_sap NULLS LAST, t.codigo;

COMMENT ON VIEW public.vw_talhoes_sap IS
  'Talhões vinculados ao retiro com código SAP para lançamento de consumo';

-- Atualiza view localidades (DROP necessário — novas colunas)
DROP VIEW IF EXISTS public.vw_localidades_sv;

CREATE VIEW public.vw_localidades_sv AS
SELECT
  id,
  nome AS local,
  codigo_sap,
  ordem_sap,
  tipo_operacional AS tipo,
  tipo AS escopo,
  lat,
  lng,
  cidade,
  uf,
  ativo
FROM public.dim_locais
ORDER BY
  ordem_sap NULLS LAST,
  CASE tipo_operacional
    WHEN 'SETOR' THEN 20
    WHEN 'LOCALIDADE' THEN 30
    WHEN 'EXTERNO' THEN 90
    ELSE 50
  END,
  nome;
