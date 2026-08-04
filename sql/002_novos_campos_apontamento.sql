-- Novos campos apontamento_campo (campos antigos permanecem)
-- Rode no Supabase SQL Editor

ALTER TABLE public.apontamento_campo
  ADD COLUMN IF NOT EXISTS inicio_turno       time,
  ADD COLUMN IF NOT EXISTS fim_turno          time,
  ADD COLUMN IF NOT EXISTS inicio_operacao    time,
  ADD COLUMN IF NOT EXISTS fim_operacao       time,
  ADD COLUMN IF NOT EXISTS talhoes            text,
  ADD COLUMN IF NOT EXISTS insumo             text,
  ADD COLUMN IF NOT EXISTS quantidade_insumo  numeric(12, 4),
  ADD COLUMN IF NOT EXISTS unidade            text;

COMMENT ON COLUMN public.apontamento_campo.inicio_turno IS 'Horário início do turno (ex: 06:31)';
COMMENT ON COLUMN public.apontamento_campo.fim_turno IS 'Horário fim do turno (ex: 18:14)';
COMMENT ON COLUMN public.apontamento_campo.inicio_operacao IS 'Horário início da operação (ex: 08:20)';
COMMENT ON COLUMN public.apontamento_campo.fim_operacao IS 'Horário fim da operação (ex: 17:00)';
COMMENT ON COLUMN public.apontamento_campo.talhoes IS 'Talhão(ões) / área (ex: córrego do campo pasto 547)';
COMMENT ON COLUMN public.apontamento_campo.insumo IS 'Insumo principal ou lista (ex: fipronil; Fordor; calda)';
COMMENT ON COLUMN public.apontamento_campo.quantidade_insumo IS 'Quantidade do insumo principal';
COMMENT ON COLUMN public.apontamento_campo.unidade IS 'Unidade (ml, L, lts, kg, GM, etc.)';
