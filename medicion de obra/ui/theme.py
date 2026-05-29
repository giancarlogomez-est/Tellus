"""Paleta y constantes visuales de la aplicación.

Los colores de superficie y texto son tuplas ``(claro, oscuro)`` que
CustomTkinter conmuta automáticamente según el modo de apariencia.
Para matplotlib (que no entiende esas tuplas) usar ``mc(color)`` que
resuelve la tupla al hex del modo activo.
"""
import customtkinter as ctk


def mc(color):
    """Resuelve un color ``(claro, oscuro)`` al hex del modo actual.

    Para usar en matplotlib y otros contextos que requieren un color
    concreto. Si recibe un string lo devuelve tal cual.
    """
    if isinstance(color, (tuple, list)):
        return color[0] if ctk.get_appearance_mode() == "Light" else color[1]
    return color


# Acentos (independientes del modo)
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

# Superficies legacy (compatibilidad)
CARD_DARK     = "#1F2937"
CARD_LIGHT    = "#F3F4F6"

# Superficies — mode-aware (claro, oscuro)
APP_BG          = ("#F5F7FB", "#0B0F14")
SIDEBAR_BG      = ("#FFFFFF", "#0f1115")
SIDEBAR_BORDER  = ("#E5E7EB", "#0f1115")
MAIN_BG         = ("#FFFFFF", "#11141a")
CARD_BG         = ("#FFFFFF", "#1F2937")
CARD_BORDER     = ("#E5E7EB", "#374151")
HOVER_BG        = ("#F3F4F6", "#1F2937")
TABLE_HOVER     = ("#FAFAFA", "#262B33")
INPUT_BG        = ("#FFFFFF", "#1F2937")
INPUT_HOVER     = ("#F3F4F6", "#374151")

# Texto — mode-aware (claro, oscuro)
TEXT        = ("#111827", "#F3F4F6")
TEXT_MUTED  = ("#6B7280", "#9CA3AF")
TEXT_FAINT  = ("#9CA3AF", "#6B7280")
TEXT_ON_DARK = "#F3F4F6"   # texto que va sobre acentos sólidos

# Colores para figuras matplotlib (claro, oscuro) — resolver con mc()
PLOT_BG       = ("#FFFFFF", "#1F2937")
PLOT_3D_BG    = ("#FFFFFF", "#1a1d23")
AXIS_FG       = ("#6B7280", "#cbd5e1")
GRID_COLOR    = ("#F3F4F6", "#374151")

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
FONT_KPI_LBL  = (FONT_FAMILY, 12)
FONT_MONO     = ("Consolas", 10)
