-- =============================================================================
-- Produtividade campo: operações com aplicação de insumos (agosto/2026+)
-- Pai intacto: apontamento_campo (sem ALTER)
-- Filhas só quando houver insumo aplicado.
-- Rode no Supabase SQL Editor ou via scripts/aplicar_fato_operacoes.py
-- =============================================================================

-- Operação/talhão vinculada ao apontamento (1 apontamento : N operações com insumo)
CREATE TABLE IF NOT EXISTS public.fato_operacoes (
  id                          serial PRIMARY KEY,
  id_apontamento              integer NOT NULL
                              REFERENCES public.apontamento_campo(id)
                              ON DELETE CASCADE,
  operacao                    text NOT NULL,
  talhao_id                   integer REFERENCES public.dim_talhoes(id),
  retiro_id                   integer REFERENCES public.dim_locais(id),
  inicio_operacao             time,
  fim_operacao                time,
  horimetro_inicial_operacao  numeric(10, 2),
  horimetro_final_operacao    numeric(10, 2),
  observacao                  text,
  criado_em                   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fato_operacoes_apontamento
  ON public.fato_operacoes(id_apontamento);

CREATE INDEX IF NOT EXISTS idx_fato_operacoes_talhao
  ON public.fato_operacoes(talhao_id)
  WHERE talhao_id IS NOT NULL;

COMMENT ON TABLE public.fato_operacoes IS
  'Operações com aplicação de insumo — FK id_apontamento → apontamento_campo.id';
COMMENT ON COLUMN public.fato_operacoes.id IS 'PK — usar em JOINs e fato_aplicacao_insumos.id_operacao';
COMMENT ON COLUMN public.fato_operacoes.id_apontamento IS 'FK → apontamento_campo.id (turno/dia)';

-- Insumos aplicados por operação (1 operação : N produtos)
CREATE TABLE IF NOT EXISTS public.fato_aplicacao_insumos (
  id            serial PRIMARY KEY,
  id_operacao   integer NOT NULL
                REFERENCES public.fato_operacoes(id)
                ON DELETE CASCADE,
  produto       text NOT NULL,
  quantidade    numeric(12, 4) NOT NULL,
  unidade       text NOT NULL,
  criado_em     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fato_aplicacao_insumos_operacao
  ON public.fato_aplicacao_insumos(id_operacao);

COMMENT ON TABLE public.fato_aplicacao_insumos IS
  'Insumos/defensivos por operação — FK id_operacao → fato_operacoes.id';
COMMENT ON COLUMN public.fato_aplicacao_insumos.id IS 'PK — identificador único da aplicação';
COMMENT ON COLUMN public.fato_aplicacao_insumos.id_operacao IS 'FK → fato_operacoes.id';

-- View gerencial: cruzamento apontamento → operação → insumo
CREATE OR REPLACE VIEW public.vw_aplicacao_insumos_campo AS
SELECT
  ac.id                    AS id_apontamento,
  ac.data,
  ac.operador,
  ac.frota,
  fo.id                    AS id_operacao,
  fo.operacao,
  fo.talhao_id,
  dt.codigo                AS talhao_codigo,
  dt.nome                  AS talhao_nome,
  fo.retiro_id,
  dl.nome                  AS retiro_nome,
  fo.inicio_operacao,
  fo.fim_operacao,
  fo.horimetro_inicial_operacao,
  fo.horimetro_final_operacao,
  fai.id                   AS id_aplicacao_insumo,
  fai.produto,
  fai.quantidade,
  fai.unidade,
  fai.criado_em            AS aplicado_em
FROM public.apontamento_campo ac
JOIN public.fato_operacoes fo
  ON fo.id_apontamento = ac.id
JOIN public.fato_aplicacao_insumos fai
  ON fai.id_operacao = fo.id
LEFT JOIN public.dim_talhoes dt
  ON dt.id = fo.talhao_id
LEFT JOIN public.dim_locais dl
  ON dl.id = fo.retiro_id;

COMMENT ON VIEW public.vw_aplicacao_insumos_campo IS
  'Cruzamento id_apontamento → id_operacao → id_aplicacao_insumo para análises gerenciais';
