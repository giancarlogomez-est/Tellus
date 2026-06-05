"""Genera PDFs desde los reportes Excel de TELLUS usando matplotlib."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import numpy as np

try:
    from PIL import Image as PILImage
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# ── Paleta para el PDF (siempre claro, es un documento imprimible) ────────────
_HDR_BG    = "#1F2937"   # encabezado de tabla  → oscuro
_HDR_FG    = "#FFFFFF"
_ALT_BG    = "#F9FAFB"   # filas alternadas
_ROW_BG    = "#FFFFFF"
_TITLE_BG  = "#2563EB"   # título de página
_TITLE_FG  = "#FFFFFF"
_BORDER    = "#D1D5DB"
_TEXT      = "#111827"
_MUTED     = "#6B7280"
_METRIC_BG = "#EFF6FF"   # bloque de métrica
_METRIC_FG = "#1E40AF"


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def _sheet_to_grid(ws: Worksheet) -> list[list[str]]:
    """Extrae las celdas usadas como lista de listas de strings."""
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        cleaned = [_fmt(c) for c in row]
        rows.append(cleaned)
    # Recortar columnas vacías al final
    max_used = 1
    for r in rows:
        for i, c in enumerate(r):
            if c.strip():
                max_used = max(max_used, i + 1)
    rows = [r[:max_used] for r in rows]
    # Quitar filas completamente vacías al inicio y al final
    while rows and not any(c.strip() for c in rows[0]):
        rows.pop(0)
    while rows and not any(c.strip() for c in rows[-1]):
        rows.pop()
    return rows


def _render_table_page(
    pdf: PdfPages,
    title: str,
    sheet_name: str,
    rows: list[list[str]],
    logo_text: str = "TELLUS",
) -> None:
    """Dibuja una página con la tabla de datos del sheet."""
    if not rows:
        return

    ncols = max(len(r) for r in rows)
    # Normalizar todas las filas al mismo número de columnas
    rows = [r + [""] * (ncols - len(r)) for r in rows]

    # Detectar fila de título (primera fila con contenido largo o única columna fusionada)
    page_title = title
    data_rows = rows
    if rows and rows[0][0].strip() and len(rows[0]) > 1:
        first_nonempty = next((c for c in rows[0] if c.strip()), "")
        if "Informe" in first_nonempty or "Cuantificación" in first_nonempty or \
                "Curva" in first_nonempty or "producción" in first_nonempty.lower():
            page_title = first_nonempty
            data_rows = rows[1:]

    # Detectar si hay fila de metadatos (proyecto:, vuelo:, etc.)
    meta_line = ""
    if data_rows and data_rows[0][0].strip().startswith("Proyecto"):
        meta_line = "  |  ".join(c for c in data_rows[0] if c.strip())
        data_rows = data_rows[1:]

    # Quitar filas vacías
    data_rows = [r for r in data_rows if any(c.strip() for c in r)]

    # Estimar tamaño de figura
    nrows = len(data_rows)
    row_h = 0.35   # pulgadas por fila
    fig_h = max(4.0, min(14.0, 2.2 + nrows * row_h))
    fig, ax = plt.subplots(figsize=(11, fig_h))
    ax.axis("off")
    fig.patch.set_facecolor("white")

    top = 1.0
    y_cursor = top - 0.02

    # ── Título de página ─────────────────────────────────────────────────────
    title_h = 0.06
    ax.add_patch(FancyBboxPatch(
        (0.0, y_cursor - title_h), 1.0, title_h,
        transform=ax.transAxes,
        boxstyle="round,pad=0.005", linewidth=0,
        facecolor=_TITLE_BG, clip_on=False,
    ))
    ax.text(0.5, y_cursor - title_h / 2, page_title,
            transform=ax.transAxes, ha="center", va="center",
            fontsize=11, fontweight="bold", color=_TITLE_FG)
    ax.text(0.98, y_cursor - title_h / 2, logo_text,
            transform=ax.transAxes, ha="right", va="center",
            fontsize=8, color="#BFDBFE", fontstyle="italic")
    y_cursor -= title_h + 0.01

    if meta_line:
        ax.text(0.01, y_cursor - 0.012, meta_line,
                transform=ax.transAxes, ha="left", va="center",
                fontsize=7.5, color=_MUTED)
        y_cursor -= 0.03

    # ── Tabla ─────────────────────────────────────────────────────────────────
    if not data_rows:
        fig.tight_layout()
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    table_top = y_cursor - 0.01
    avail_h = table_top          # fracción de axes disponible para la tabla
    row_frac = min(avail_h / (nrows + 1), 0.045)  # +1 para cabecera

    col_widths = _estimate_col_widths(data_rows, ncols)

    # Detectar fila de cabecera (primera con fondo oscuro → típicamente vacía en texto pero...)
    # Usamos heurística: si la fila tiene textos que parecen encabezados (sin números grandes)
    hdr_idx = None
    for i, r in enumerate(data_rows):
        non_empty = [c for c in r if c.strip()]
        if non_empty and not any(
            c.replace(",", "").replace(".", "").replace("-", "").lstrip().isdigit()
            for c in non_empty
        ):
            if any(keyword in " ".join(non_empty).lower()
                   for keyword in ["fecha", "vuelo", "corte", "relleno", "progresiva",
                                   "balance", "sección", "producción", "avance"]):
                hdr_idx = i
                break

    for i, row in enumerate(data_rows):
        y_row = table_top - i * row_frac - row_frac

        # Color de fondo
        if i == hdr_idx:
            bg = _HDR_BG
        elif any("TOTAL" in c.upper() for c in row if c.strip()):
            bg = _HDR_BG
        elif i % 2 == 0:
            bg = _ALT_BG
        else:
            bg = _ROW_BG

        fg = _HDR_FG if bg == _HDR_BG else _TEXT
        fs = 7.0 if bg == _HDR_BG else 6.8
        fw = "bold" if bg == _HDR_BG else "normal"

        # Barra de fondo de la fila
        ax.add_patch(FancyBboxPatch(
            (0.0, y_row), 1.0, row_frac - 0.002,
            transform=ax.transAxes,
            boxstyle="square,pad=0", linewidth=0.3,
            edgecolor=_BORDER, facecolor=bg, clip_on=False,
        ))

        # Texto de cada celda
        x_cursor = 0.005
        for j, cell in enumerate(row):
            w = col_widths[j] if j < len(col_widths) else 0.1
            # Alineación: primera columna izquierda, resto derecha si parece número
            is_num = cell.replace(",", "").replace(".", "").replace("-", "").strip().isdigit()
            ha = "right" if (is_num and j > 0) else "left"
            x_text = x_cursor + w - 0.005 if ha == "right" else x_cursor + 0.005
            ax.text(
                x_text, y_row + row_frac * 0.5,
                cell,
                transform=ax.transAxes,
                ha=ha, va="center",
                fontsize=fs, fontweight=fw, color=fg,
                clip_on=True,
            )
            x_cursor += w

    # ── Pie de página ─────────────────────────────────────────────────────────
    y_foot = table_top - nrows * row_frac - 0.02
    ax.plot([0, 1], [max(y_foot, 0.01), max(y_foot, 0.01)],
            transform=ax.transAxes, color=_BORDER, lw=0.5, clip_on=False)
    ax.text(0.01, max(y_foot - 0.015, 0.005),
            f"Hoja: {sheet_name}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6, color=_MUTED)

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    pdf.savefig(fig, bbox_inches="tight", dpi=150)
    plt.close(fig)


def _estimate_col_widths(rows: list[list[str]], ncols: int) -> list[float]:
    """Estima anchos de columna proporcionales al contenido."""
    char_counts = [0] * ncols
    for row in rows:
        for j, cell in enumerate(row):
            if j < ncols:
                char_counts[j] = max(char_counts[j], len(cell))
    total = sum(char_counts) or 1
    # Primera columna suele ser la más ancha (etiquetas)
    widths = [max(c / total, 0.04) for c in char_counts]
    # Normalizar a 1.0
    s = sum(widths)
    return [w / s for w in widths]


def _render_image_page(pdf: PdfPages, img_path: Path, title: str = "") -> None:
    """Renderiza una imagen PNG en una página completa."""
    if not _PIL_OK or not img_path.exists():
        return
    img = PILImage.open(img_path)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    ax.imshow(img, aspect="auto")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold",
                     color=_TEXT, pad=8)
    fig.tight_layout(pad=0.5)
    pdf.savefig(fig, bbox_inches="tight", dpi=150)
    plt.close(fig)


def _render_resumen_diario(pdf: PdfPages, ws: Worksheet, project_name: str) -> None:
    """Renderiza la hoja 'Resumen' del informe diario con bloques de métricas."""
    # Leer métricas (columnas A y B: etiqueta, valor)
    title_str = ""
    metrics: list[tuple[str, str, str]] = []  # (section, label, value+unit)
    section = ""

    for row in ws.iter_rows(values_only=True):
        a = _fmt(row[0]) if len(row) > 0 else ""
        b = _fmt(row[1]) if len(row) > 1 else ""
        c = _fmt(row[2]) if len(row) > 2 else ""

        if "Informe Diario" in a:
            title_str = a
        elif "PRODUCCIÓN" in a.upper() or "ACUMULADO" in a.upper():
            section = a
        elif a.strip() and a.strip().startswith("Proyecto"):
            pass  # skip meta
        elif a.strip() and b.strip():
            metrics.append((section, a, f"{b} {c}".strip()))

    if not metrics:
        grid = _sheet_to_grid(ws)
        _render_table_page(pdf, title_str or "Resumen", "Resumen", grid)
        return

    # Dibujar página de métricas
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Título
    ax.add_patch(FancyBboxPatch(
        (0.0, 0.93), 1.0, 0.065,
        transform=ax.transAxes,
        boxstyle="round,pad=0.005", linewidth=0,
        facecolor=_TITLE_BG, clip_on=False,
    ))
    ax.text(0.5, 0.963, title_str or "Informe Diario de Avance",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=12, fontweight="bold", color=_TITLE_FG)
    ax.text(0.98, 0.963, project_name,
            transform=ax.transAxes, ha="right", va="center",
            fontsize=8, color="#BFDBFE", fontstyle="italic")

    # Métricas en cuadrícula
    sections_order: list[str] = []
    by_section: dict[str, list[tuple[str, str]]] = {}
    for sec, lbl, val in metrics:
        if sec not in by_section:
            by_section[sec] = []
            sections_order.append(sec)
        by_section[sec].append((lbl, val))

    y = 0.88
    for sec in sections_order:
        items = by_section[sec]
        if sec:
            ax.add_patch(FancyBboxPatch(
                (0.0, y - 0.028), 1.0, 0.030,
                transform=ax.transAxes,
                boxstyle="square,pad=0", linewidth=0,
                facecolor=_HDR_BG, clip_on=False,
            ))
            ax.text(0.01, y - 0.013, sec,
                    transform=ax.transAxes, ha="left", va="center",
                    fontsize=9, fontweight="bold", color=_HDR_FG)
            y -= 0.035

        cols = 3
        for idx, (lbl, val) in enumerate(items):
            col = idx % cols
            row_offset = idx // cols
            x = 0.01 + col * 0.33
            y_item = y - row_offset * 0.075

            ax.add_patch(FancyBboxPatch(
                (x, y_item - 0.06), 0.31, 0.065,
                transform=ax.transAxes,
                boxstyle="round,pad=0.008", linewidth=0.5,
                edgecolor=_BORDER, facecolor=_METRIC_BG, clip_on=False,
            ))
            ax.text(x + 0.01, y_item - 0.022, lbl,
                    transform=ax.transAxes, ha="left", va="center",
                    fontsize=7.5, color=_MUTED)
            ax.text(x + 0.155, y_item - 0.044, val,
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=11, fontweight="bold", color=_METRIC_FG)

        rows_used = (len(items) + cols - 1) // cols
        y -= rows_used * 0.075 + 0.02

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    pdf.savefig(fig, bbox_inches="tight", dpi=150)
    plt.close(fig)


def generar_pdf_desde_xlsx(
    ruta_xlsx: Path,
    heatmap_path: Path | None = None,
) -> Path:
    """Lee el xlsx y genera un PDF en la misma carpeta con el mismo nombre base.

    Retorna la ruta al PDF generado.
    """
    pdf_path = ruta_xlsx.with_suffix(".pdf")
    wb = openpyxl.load_workbook(str(ruta_xlsx), data_only=True)

    # Leer nombre de proyecto desde la primera hoja
    project_name = ""
    ws0 = wb[wb.sheetnames[0]]
    for row in ws0.iter_rows(values_only=True):
        for cell in row:
            if cell and "Proyecto:" in str(cell):
                project_name = str(cell).replace("Proyecto:", "").strip()
                break
        if project_name:
            break

    # Título general desde la primera fila de la primera hoja
    general_title = ""
    for row in ws0.iter_rows(min_row=1, max_row=2, values_only=True):
        for cell in row:
            if cell and isinstance(cell, str) and "Informe" in cell:
                general_title = cell
                break
        if general_title:
            break

    with PdfPages(str(pdf_path)) as pdf:
        # Metadata del PDF
        d = pdf.infodict()
        d["Title"] = general_title or ruta_xlsx.stem
        d["Author"] = "TELLUS — Medición de Volúmenes"
        d["Subject"] = project_name

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            if sheet_name == "Resumen":
                _render_resumen_diario(pdf, ws, project_name)
            else:
                grid = _sheet_to_grid(ws)
                if grid:
                    _render_table_page(pdf, general_title or sheet_name,
                                       sheet_name, grid)

        # Página de heatmap si existe
        if heatmap_path and heatmap_path.exists():
            _render_image_page(pdf, heatmap_path, "Mapa de calor de producción")

    return pdf_path
