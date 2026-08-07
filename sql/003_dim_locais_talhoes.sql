-- =============================================================================
-- Localidades SV — evolui dim_locais (planilha DIM_LOCALIDADES_SV) + dim_talhoes
-- Não cria dim_localidades_sv / dim_retiros duplicadas.
-- Rode no Supabase SQL Editor ou via scripts/aplicar_dim_locais_talhoes.py
-- =============================================================================

-- 1) Classificação operacional (RETIRO 1..6, LOCALIDADE, SETOR, EXTERNO)
ALTER TABLE public.dim_locais
  ADD COLUMN IF NOT EXISTS tipo_operacional text;

COMMENT ON COLUMN public.dim_locais.tipo_operacional IS
  'Classificação operacional SV: RETIRO 1..6, RETIRO, LOCALIDADE, SETOR, EXTERNO';

-- 2) Retiros e localidades internas já cadastradas (por id estável)
UPDATE public.dim_locais SET tipo_operacional = 'RETIRO 1'   WHERE id = 1;
UPDATE public.dim_locais SET tipo_operacional = 'RETIRO 6'   WHERE id = 2;
UPDATE public.dim_locais SET tipo_operacional = 'RETIRO 5'   WHERE id = 3;
UPDATE public.dim_locais SET tipo_operacional = 'RETIRO 2'   WHERE id = 4;
UPDATE public.dim_locais SET tipo_operacional = 'RETIRO 4'   WHERE id = 5;
UPDATE public.dim_locais SET tipo_operacional = 'RETIRO 3'   WHERE id = 6;
UPDATE public.dim_locais SET tipo_operacional = 'LOCALIDADE' WHERE id = 7;
UPDATE public.dim_locais SET tipo_operacional = 'LOCALIDADE' WHERE id = 8;
UPDATE public.dim_locais SET tipo_operacional = 'SETOR'      WHERE id = 9;
UPDATE public.dim_locais SET tipo_operacional = 'LOCALIDADE' WHERE id = 10;

-- Cidades externas (viagens)
UPDATE public.dim_locais SET tipo_operacional = 'EXTERNO' WHERE id BETWEEN 11 AND 17;

-- 3) Registros da planilha ainda ausentes
INSERT INTO public.dim_locais (nome, tipo, tipo_operacional, cidade, uf, pais, ativo)
SELECT v.nome, 'INTERNO', v.tipo_operacional, 'Bataguassu', 'MS', 'Brasil', true
FROM (VALUES
  ('ALDEIA I',            'LOCALIDADE'),
  ('ALDEIA II',           'LOCALIDADE'),
  ('VIVEIRO',             'SETOR'),
  ('SEDE',                'RETIRO'),
  ('TORRE',               'LOCALIDADE'),
  ('ESTRADA PRINCIPAL',   'LOCALIDADE')
) AS v(nome, tipo_operacional)
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_locais d
  WHERE upper(trim(d.nome)) = upper(trim(v.nome))
);

-- 4) View compatível com nomenclatura da planilha
CREATE OR REPLACE VIEW public.vw_localidades_sv AS
SELECT
  id,
  nome AS local,
  tipo_operacional AS tipo,
  tipo AS escopo,
  lat,
  lng,
  cidade,
  uf,
  ativo
FROM public.dim_locais
ORDER BY
  CASE tipo_operacional
    WHEN 'RETIRO 1' THEN 10
    WHEN 'RETIRO 2' THEN 11
    WHEN 'RETIRO 3' THEN 12
    WHEN 'RETIRO 4' THEN 13
    WHEN 'RETIRO 5' THEN 14
    WHEN 'RETIRO 6' THEN 15
    WHEN 'RETIRO' THEN 16
    WHEN 'SETOR' THEN 20
    WHEN 'LOCALIDADE' THEN 30
    WHEN 'EXTERNO' THEN 90
    ELSE 50
  END,
  nome;

COMMENT ON VIEW public.vw_localidades_sv IS
  'Localidades operacionais SV — leitura alinhada à planilha DIM_LOCALIDADES_SV (fonte: dim_locais).';

-- 5) Talhões (novo — FK para dim_locais)
CREATE TABLE IF NOT EXISTS public.dim_talhoes (
  id            serial PRIMARY KEY,
  codigo        text,
  nome          text NOT NULL,
  id_local      integer REFERENCES public.dim_locais(id),
  observacao    text,
  ativo         boolean NOT NULL DEFAULT true,
  criado_em     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dim_talhoes_local ON public.dim_talhoes(id_local);
CREATE INDEX IF NOT EXISTS idx_dim_talhoes_codigo ON public.dim_talhoes(codigo) WHERE codigo IS NOT NULL;

COMMENT ON TABLE public.dim_talhoes IS
  'Talhões/pastos vinculados a localidade (dim_locais). Ex.: pasto 547 no RETIRO CÓRREGO DO CAMPO.';

-- Exemplo inicial (pasto 547 — apontamento campo)
INSERT INTO public.dim_talhoes (codigo, nome, id_local, observacao)
SELECT '547', 'PASTO 547', d.id, 'Córrego do campo — referência apontamento'
FROM public.dim_locais d
WHERE upper(trim(d.nome)) = 'RETIRO CORREGO DO CAMPO'
  AND NOT EXISTS (
    SELECT 1 FROM public.dim_talhoes t WHERE t.codigo = '547'
  );
