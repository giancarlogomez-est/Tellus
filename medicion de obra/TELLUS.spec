# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para TELLUS — Medición de Volúmenes en Obras Viales
Empaqueta todas las dependencias geoespaciales (rasterio, geopandas,
pyproj, shapely) y la UI CustomTkinter en un directorio distribuible.
"""
import sys
from pathlib import Path
import customtkinter
import pyproj
import rasterio
import matplotlib
import pyogrio

SRC = Path(SPECPATH)

# ── Datos de librerías externas que PyInstaller no detecta automáticamente ──
datas = [
    # Temas e imágenes de CustomTkinter
    (str(Path(customtkinter.__file__).parent), "customtkinter"),
    # Datos de proyección PROJ (necesarios para pyproj / geopandas)
    (str(Path(pyproj.__file__).parent / "proj_dir"), "pyproj/proj_dir"),
    # Datos de Matplotlib (fuentes, estilos)
    (str(Path(matplotlib.__file__).parent / "mpl-data"), "matplotlib/mpl-data"),
    # Drivers de pyogrio (geopandas)
    (str(Path(pyogrio.__file__).parent), "pyogrio"),
    # Recursos del propio proyecto
    (str(SRC / "ui"), "ui"),
]

# Archivos de datos de rasterio (GDAL/PROJ embebidos)
rasterio_pkg = Path(rasterio.__file__).parent
for pattern in ("*.dll", "gdal_data/**/*", "proj_data/**/*"):
    for f in rasterio_pkg.glob(pattern):
        rel = f.relative_to(rasterio_pkg)
        datas.append((str(f), f"rasterio/{rel.parent}"))

hidden_imports = [
    # rasterio drivers
    "rasterio._shim", "rasterio.control", "rasterio.crs",
    "rasterio.enums", "rasterio.env", "rasterio.errors",
    "rasterio.features", "rasterio.mask", "rasterio.merge",
    "rasterio.plot", "rasterio.transform", "rasterio.warp",
    "rasterio._warp", "rasterio.vrt",
    # pyproj
    "pyproj.datadir", "pyproj._transformer",
    # shapely
    "shapely", "shapely.geometry", "shapely.ops",
    # geopandas / pyogrio
    "geopandas", "geopandas.io.file", "pyogrio", "pyogrio._compat",
    # matplotlib backends
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_agg",
    # pandas / numpy
    "pandas", "numpy",
    # openpyxl
    "openpyxl", "openpyxl.styles", "openpyxl.utils",
    "openpyxl.drawing.image",
    # ezdxf
    "ezdxf",
    # PIL
    "PIL", "PIL.Image", "PIL.ImageTk",
    # UI interna
    "ui", "ui.app", "ui.state", "ui.theme",
    "ui.view_dashboard", "ui.view_diario", "ui.view_dron",
    "ui.view_equipos", "ui.view_reportes", "ui.view_config",
    "ui.view_3d", "ui.view_perfil", "ui.widgets", "ui.runner",
    "ui.dem_utils", "ui.eje_utils", "ui.basemap", "ui.pdf_utils",
    # PDF generation
    "matplotlib.backends.backend_pdf",
    # stdlib que PyInstaller a veces omite
    "tkinter", "tkinter.messagebox", "tkinter.filedialog",
    "threading", "json", "shutil",
]

a = Analysis(
    [str(SRC / "app.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "jupyter", "notebook", "sphinx"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,         # modo --onedir (más rápido al arrancar)
    name="TELLUS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                 # sin ventana de consola
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TELLUS",
)
