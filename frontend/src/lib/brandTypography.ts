/** Site-wide brand face — login “Fikiri Solutions” treatment */
export const BRAND_FONT_FAMILY = '"Source Serif 4", Georgia, "Times New Roman", serif'

/** Recharts axis / legend tick style */
export const chartTickStyle = (opts?: { fontSize?: number; fill?: string }) => ({
  fontFamily: BRAND_FONT_FAMILY,
  fontSize: opts?.fontSize ?? 12,
  fill: opts?.fill ?? '#6B7280',
})
