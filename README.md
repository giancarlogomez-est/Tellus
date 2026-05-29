# Automatización de Medición de Volúmenes en Obras Viales

Sistema completo para medir volúmenes de tierra en tiempo real durante la ejecución de obras viales, usando herramientas de bajo costo (dron consumer + software libre).

---

## ⚡ Interfaz gráfica — VolumenView

Para usar el proyecto sin necesidad de línea de comandos:

```
Doble clic en  VolumenView.bat
```

o desde terminal:

```
pip install customtkinter pillow
python app.py
```

La aplicación incluye:

- **Dashboard** — KPIs y gráficos de producción diaria, acumulado vs. objetivo.
- **Vuelo diario** — selector de fecha y ejecución del pipeline con un clic.
- **Comparativo Pre/Post** — flujo de dron único para mediciones puntuales.
- **Reportes** — explorador de Excel y vista previa de heatmaps generados.
- **Configuración** — formulario que edita `proyecto_config.json` sin tocar JSON.

La interfaz envuelve los scripts existentes (`pipeline.py`, `calculo_volumen_odm.py`)
sin modificar su lógica.

---

## Estructura de Carpetas

```
medicion de obra/
├── app.py                     → Punto de entrada de la interfaz gráfica
├── VolumenView.bat            → Lanzador de un clic (Windows)
├── ui/                        → Código de la interfaz (CustomTkinter)
│
├── 02_dron_odm/               → Método dron + OpenDroneMap
│   ├── calculo_volumen_odm.py ← Script principal
│   └── generar_dems_ejemplo.py
│
├── 03_pipeline_diario/        → Sistema de avance continuo
│   ├── pipeline.py            ← Corre cada día después del vuelo
│   ├── configurar_proyecto.py ← Corre UNA VEZ al inicio
│   └── generar_serie_ejemplo.py
│
├── baseline/                  ← DEBES COLOCAR AQUÍ:
│   ├── dem_baseline.tif       ← DSM del vuelo de referencia (antes de obra)
│   └── eje_via.geojson        ← Eje exportado de Civil 3D o QGIS
│
├── vuelos/                    ← Un directorio por fecha de vuelo
│   └── YYYY-MM-DD/
│       └── dsm.tif            ← DSM generado por OpenDroneMap
│
├── reportes/
│   ├── diarios/               → reporte_YYYY-MM-DD.xlsx + heatmap_.png
│   ├── semanales/             → reporte_YYYY-Wnn.xlsx  (se genera los lunes)
│   └── mensuales/             → reporte_YYYY-MM.xlsx + superficies.xml
│
├── proyecto_config.json       ← Parámetros del proyecto
├── registro.csv               ← Historial de todos los vuelos
└── registro_secciones.csv     ← Detalle por progresiva
```

---

## Flujos de Trabajo

### Flujo 1 — Dron + OpenDroneMap (vuelo único)

Para calcular volúmenes de un par de vuelos pre/post.

**Requisitos:**
```
pip install rasterio numpy geopandas shapely matplotlib openpyxl scipy
```

**Pasos:**
1. Coloca en `02_dron_odm/`:
   - `dem_pre.tif`  → DSM del vuelo de referencia
   - `dem_post.tif` → DSM del vuelo de medición
   - `eje_via.geojson` → Eje de la vía (exportado de Civil 3D o QGIS)
2. Ajustar parámetros al inicio del script (progresiva, espaciado, ancho)
3. Correr:
   ```
   cd 02_dron_odm
   python calculo_volumen_odm.py
   ```

**Salidas:**
- `reporte_volumen_odm.xlsx` — tabla por progresiva + resumen
- `diferencia_dem.tif` — raster ΔZ (apto para QGIS)
- `heatmap_volumenes.png` — mapa de calor
- `superficies_civil3d.xml` — importar en Civil 3D: *Insertar → Importar LandXML*

**Para probar con DEMs sintéticos:**
```
python generar_dems_ejemplo.py
python calculo_volumen_odm.py
```

---

### Flujo 2 — Pipeline Diario (vuelos continuos)

Sistema de seguimiento automático con reportes diarios, semanales y mensuales.

**Primera vez — configurar el proyecto:**
```
cd 03_pipeline_diario
python configurar_proyecto.py
```

Luego copiar a `baseline/`:
- `dem_baseline.tif` — DSM antes de iniciar la obra
- `eje_via.geojson` — Eje de la vía

**Flujo de cada día:**
```
1. Volar con el dron
2. Procesar en OpenDroneMap → dsm.tif
3. Copiar:  vuelos/2025-05-08/dsm.tif
4. Correr:  python pipeline.py --fecha 2025-05-08
```

**Reportes generados automáticamente:**
- Cada día → `reportes/diarios/reporte_YYYY-MM-DD.xlsx` + heatmap
- Cada lunes → `reportes/semanales/reporte_YYYY-Wnn.xlsx`
- Día 1 de cada mes → `reportes/mensuales/reporte_YYYY-MM.xlsx` + LandXML

**Para probar con datos sintéticos (7 días):**
```
python generar_serie_ejemplo.py
python pipeline.py --fecha 2025-05-05
python pipeline.py --fecha 2025-05-06
...
```

---

## Notas sobre el DJI Mini 5 Pro

Compatible con este flujo. Para obtener precisión aceptable (±5–10 cm vertical):
- Volar a 60–70 m de altura → GSD ≈ 2.0–2.5 cm/px
- Solapamiento 85% frontal / 75% lateral
- Usar 4–6 GCPs por sección de 300 m, medidos con GPS diferencial
- Procesar en OpenDroneMap con `--gcp gcps.txt`

---

## Dependencias

```
pip install pandas numpy openpyxl rasterio geopandas shapely matplotlib scipy ezdxf
pip install customtkinter pillow            # solo para la interfaz gráfica
```

---

*Proyecto académico — ESING Posgrado en Vías, 2025*
