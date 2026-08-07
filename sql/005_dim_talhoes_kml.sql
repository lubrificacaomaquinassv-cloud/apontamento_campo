-- Suporte à carga em massa de talhões (KML)
ALTER TABLE public.dim_talhoes
  ADD COLUMN IF NOT EXISTS area_ha numeric(10, 4),
  ADD COLUMN IF NOT EXISTS classe_uso text;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_talhoes_codigo
  ON public.dim_talhoes (codigo)
  WHERE codigo IS NOT NULL AND trim(codigo) <> '';

COMMENT ON COLUMN public.dim_talhoes.area_ha IS 'Área em hectares (fonte KML)';
COMMENT ON COLUMN public.dim_talhoes.classe_uso IS 'Classe uso solo: Silvicultura, Silvipastoril, Pastagem, TIP';
