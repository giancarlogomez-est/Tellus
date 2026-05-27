"""Paleta y constantes visuales de la aplicación."""

# Acentos
PRIMARY      = "#2563EB"   # azul de marca
PRIMARY_HOV  = "#1D4ED8"
SUCCESS      = "#10B981"
SUCCESS_HOV  = "#059669"
WARNING      = "#F59E0B"
DANGER       = "#EF4444"
DANGER_HOV   = "#DC2626"

# Volúmenes — convención del mockup: cortes = rojo, llenos = verde
CORTE_COLOR    = "#EF4444"   # rojo
CORTE_LIGHT    = "#F87171"
RELLENO_COLOR  = "#10B981"   # verde
RELLENO_LIGHT  = "#34D399"
BALANCE_POS    = "#10B981"
BALANCE_NEG    = "#EF4444"

# Superficies — tema oscuro (vistas existentes)
CARD_DARK     = "#1F2937"
CARD_LIGHT    = "#F3F4F6"

# Superficies — tema claro (dashboard estilo mockup)
APP_BG          = "#F5F7FB"
CARD_BG         = "#FFFFFF"
CARD_BORDER     = "#E5E7EB"
HOVER_BG        = "#F3F4F6"
TABLE_HOVER     = "#FAFAFA"

# Texto
TEXT        = "#111827"
TEXT_MUTED  = "#6B7280"
TEXT_FAINT  = "#9CA3AF"

# Chips de KPI (background, foreground) — mockup
CHIP = {
    "orange": ("#FFF3E6", "#F59E0B"),
    "green":  ("#E7F7EE", "#10B981"),
    "red":    ("#FEE2E2", "#EF4444"),
    "dark":   ("#EEF2FF", "#4338CA"),
    "purple": ("#F3E8FF", "#9333EA"),
    "blue":   ("#E0F2FE", "#0284C7"),
    "indigo": ("#E0E7FF", "#4F46E5"),
}

# Tipografía
FONT_FAMILY   = "Segoe UI"
FONT_TITLE    = (FONT_FAMILY, 22, "bold")
FONT_H1       = (FONT_FAMILY, 18, "bold")
FONT_H2       = (FONT_FAMILY, 13, "bold")
FONT_BODY     = (FONT_FAMILY, 11)
FONT_SMALL    = (FONT_FAMILY, 10)
FONT_TINY     = (FONT_FAMILY, 9)
FONT_KPI      = (FONT_FAMILY, 22, "bold")
FONT_KPI_LBL  = (FONT_FAMILY, 10)
FONT_MONO     = ("Consolas", 10)
