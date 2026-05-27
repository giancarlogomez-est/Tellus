"""
Módulo de procesamiento de DEMs (Modelos Digitales de Elevación).

Responsable de:
    - Lectura y validación de archivos GeoTIFF.
    - Validación / reproyección al CRS objetivo definido por el usuario.
    - Alineación espacial entre rásters (resampling al ráster de referencia).
    - Álgebra de mapas: cálculo de cortes y rellenos (cut & fill).
    - Cubicación de volúmenes a partir de espesores y resolución de píxel.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
from rasterio.io import MemoryFile


@dataclass
class RasterData:
    """Estructura ligera que encapsula un ráster ya validado en memoria."""
    array: np.ndarray            # Matriz de elevaciones (Z)
    transform: rasterio.Affine   # Transformación afín (geo-referenciación)
    crs: rasterio.crs.CRS        # Sistema de coordenadas
    nodata: Optional[float]      # Valor sin dato
    pixel_area: float            # Área de un píxel en m² (asume CRS proyectado)
    profile: dict                # Perfil rasterio completo (para reproyección)


def load_raster(file_obj, target_epsg: int) -> RasterData:
    """
    Carga un GeoTIFF desde un objeto de archivo (uploader de Streamlit o ruta).

    Si el CRS del ráster no coincide con `target_epsg`, se reproyecta EN MEMORIA
    (sin escribir a disco) para garantizar consistencia entre las capas.

    Args:
        file_obj: BytesIO / UploadedFile / ruta de archivo.
        target_epsg: Código EPSG objetivo (ej. 3116 para MAGNA-SIRGAS Bogotá).

    Returns:
        Instancia de RasterData lista para álgebra de mapas.
    """
    target_crs = rasterio.crs.CRS.from_epsg(target_epsg)

    # Permitir tanto rutas como buffers en memoria (Streamlit entrega bytes)
    if hasattr(file_obj, "read"):
        data_bytes = file_obj.read()
        src_ctx = MemoryFile(data_bytes).open()
    else:
        src_ctx = rasterio.open(file_obj)

    with src_ctx as src:
        if src.crs == target_crs:
            # CRS coincide: lectura directa
            array = src.read(1).astype("float32")
            transform = src.transform
            profile = src.profile.copy()
            crs = src.crs
        else:
            # Reproyección en memoria al CRS objetivo
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            array = np.empty((height, width), dtype="float32")
            reproject(
                source=rasterio.band(src, 1),
                destination=array,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
            )
            profile = src.profile.copy()
            profile.update(
                crs=target_crs, transform=transform,
                width=width, height=height,
            )
            crs = target_crs

        nodata = src.nodata
        # Área de píxel en m² (válido si el CRS está en metros)
        pixel_area = abs(transform.a * transform.e)

    # Enmascarar nodata para no contaminar el álgebra
    if nodata is not None:
        array = np.where(array == nodata, np.nan, array)

    return RasterData(
        array=array,
        transform=transform,
        crs=crs,
        nodata=nodata,
        pixel_area=pixel_area,
        profile=profile,
    )


def align_rasters(reference: RasterData, target: RasterData) -> RasterData:
    """
    Alinea `target` a la grilla de `reference` mediante remuestreo bilineal.

    Necesario antes de hacer álgebra de mapas: ambas matrices deben tener
    la misma forma, transformación y CRS.
    """
    if (
        reference.array.shape == target.array.shape
        and reference.transform == target.transform
    ):
        return target  # Ya están alineados

    dst_array = np.empty(reference.array.shape, dtype="float32")
    reproject(
        source=target.array,
        destination=dst_array,
        src_transform=target.transform,
        src_crs=target.crs,
        dst_transform=reference.transform,
        dst_crs=reference.crs,
        resampling=Resampling.bilinear,
    )
    return RasterData(
        array=dst_array,
        transform=reference.transform,
        crs=reference.crs,
        nodata=target.nodata,
        pixel_area=reference.pixel_area,
        profile=reference.profile,
    )


def cut_fill_volume(
    surface_initial: RasterData,
    surface_final: RasterData,
) -> dict:
    """
    Calcula corte / relleno entre dos superficies.

    Convención: `surface_initial` es la superficie ANTES (terreno natural o día
    anterior) y `surface_final` es DESPUÉS (avance o diseño).

    Δh = surface_final - surface_initial
        - Δh > 0  → relleno (se agregó material)
        - Δh < 0  → corte   (se removió material)

    Returns:
        dict con volúmenes en m³, áreas en m² y matriz de espesores.
    """
    final = align_rasters(surface_initial, surface_final)
    delta_h = final.array - surface_initial.array

    pixel_area = surface_initial.pixel_area
    valid = ~np.isnan(delta_h)

    fill_mask = (delta_h > 0) & valid
    cut_mask = (delta_h < 0) & valid

    fill_volume = float(np.nansum(delta_h[fill_mask]) * pixel_area)
    cut_volume = float(-np.nansum(delta_h[cut_mask]) * pixel_area)  # positivo
    net_volume = fill_volume - cut_volume                            # balance

    return {
        "volumen_corte_m3": round(cut_volume, 2),
        "volumen_relleno_m3": round(fill_volume, 2),
        "volumen_neto_m3": round(net_volume, 2),
        "area_corte_m2": round(float(cut_mask.sum() * pixel_area), 2),
        "area_relleno_m2": round(float(fill_mask.sum() * pixel_area), 2),
        "espesor_promedio_m": round(float(np.nanmean(np.abs(delta_h))), 3),
        "delta_h": delta_h,  # matriz para visualización opcional
    }


def daily_executed_volume(
    surface_yesterday: RasterData,
    surface_today: RasterData,
) -> float:
    """
    Volumen ejecutado en el día (valor absoluto del balance neto).

    Útil para alimentar el cálculo de rendimientos de maquinaria.
    """
    result = cut_fill_volume(surface_yesterday, surface_today)
    return abs(result["volumen_neto_m3"])


def pavement_layer_volume(
    survey_surface: RasterData,
    design_surface: RasterData,
    layer_thickness_m: float,
) -> dict:
    """
    Cubica una capa estructural de pavimento.

    Estrategia:
        1. Calcula el área efectiva donde el levantamiento (`survey_surface`)
           está por debajo de la superficie de diseño (`design_surface`)
           dentro del espesor teórico de la capa.
        2. Volumen = área válida × espesor teórico.

    Args:
        survey_surface: DEM del levantamiento topográfico actual.
        design_surface: DEM de la superficie superior de la capa de diseño.
        layer_thickness_m: Espesor teórico de la capa (metros).

    Returns:
        dict con área cubierta (m²) y volumen estimado (m³).
    """
    survey = align_rasters(design_surface, survey_surface)
    delta = design_surface.array - survey.array
    valid = (~np.isnan(delta)) & (delta >= 0) & (delta <= layer_thickness_m * 1.5)
    area_m2 = float(valid.sum() * design_surface.pixel_area)
    volume_m3 = area_m2 * layer_thickness_m
    return {
        "area_m2": round(area_m2, 2),
        "espesor_teorico_m": layer_thickness_m,
        "volumen_m3": round(volume_m3, 2),
    }
