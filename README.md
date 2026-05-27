# Mensure v2.0

Software con dashboard en Python para **cálculo de movimiento de tierras**,
**cubicación de capas de pavimento** y **control de rendimientos de maquinaria
pesada** a partir de DEMs (GeoTIFF) diarios.

## Arquitectura

```
Mensure v2.0/
├── run.bat                       # Lanzador en Windows
├── requirements.txt
├── config/
│   └── settings.py               # CRS comunes, tipos de maquinaria, capas
├── src/
│   ├── frontend/
│   │   ├── dashboard.py          # Vista "Resumen general" (mockup)
│   │   ├── styles.py             # CSS global (cards, sidebar, KPIs)
│   │   ├── components/
│   │   │   ├── sidebar.py        # Sidebar de navegación
│   │   │   ├── kpi_cards.py      # KPI cards con icono + delta
│   │   │   ├── charts.py         # Plotly (barras apiladas, donut)
│   │   │   └── tables.py         # Tablas HTML estilizadas
│   │   └── pages/
│   │       └── 1_Procesamiento.py  # Carga DEM + maquinaria + Excel
│   └── backend/
│       ├── raster_processor.py   # Carga/reproyección DEMs + álgebra de mapas
│       ├── machinery.py          # Cálculo de rendimientos m³/h
│       └── excel_export.py       # Reporte multi-pestaña + histórico
├── data/
│   ├── raw/                      # DEMs originales (input)
│   └── processed/                # historico_acumulado.xlsx
└── reports/                      # Reportes diarios .xlsx exportados
```

### Flujo de datos

```
[Usuario] ──drag&drop──> [Dashboard Streamlit]
                                 │
                                 │   CRS objetivo (EPSG)
                                 ▼
                       [raster_processor]
                         load_raster() ─ reproyección en memoria
                         cut_fill_volume() ─ álgebra de mapas
                         pavement_layer_volume() ─ cubicación capas
                                 │
                                 ▼
                          [machinery]
                         compute_yields() ─ m³/h por equipo y flota
                                 │
                                 ▼
                         [excel_export]
                         export_report() ─ .xlsx + histórico
                                 │
                                 ▼
                       [download_button]
```

### Flujo de estado de la UI (st.session_state)

| Clave             | Tipo            | Función                                                  |
|-------------------|-----------------|----------------------------------------------------------|
| `records`         | `list[dict]`    | Lista de equipos del día (formulario dinámico).          |
| `results`         | `dict`          | Outputs del último cálculo (volúmenes + rendimientos).   |
| `report_buffer`   | `bytes`         | Contenido del .xlsx generado, listo para descarga.       |
| `report_filename` | `str`           | Nombre sugerido del archivo descargable.                 |

## Instalación

```powershell
# (recomendado) crear venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Dependencias
pip install -r requirements.txt
```

> En Windows, `rasterio` requiere ruedas binarias precompiladas: si `pip install`
> falla, instalar previamente con `pip install rasterio --only-binary=rasterio`.

## Ejecución

```powershell
streamlit run src\frontend\dashboard.py
```

O ejecutar `run.bat` con doble clic.

## Uso del dashboard

1. **Sidebar:** define la fecha de la jornada y el CRS (EPSG). Los DEMs que no
   estén en ese CRS se reproyectan automáticamente en memoria.
2. **Carga DEMs:** arrastra los archivos GeoTIFF de Terreno Natural, Diseño y
   Avance del día.
3. **(Opcional) Pavimentos:** marca el check y ajusta los espesores teóricos.
4. **Registro de maquinaria:** agrega cada equipo (tipo, ID y horas operativas).
5. **Ejecutar cálculo:** procesa volúmenes y rendimientos.
6. **Descargar reporte:** genera el `.xlsx` con pestañas Resumen Diario,
   Rendimientos, Resumen Flota, Pavimentos e Histórico Acumulado.

## Convenciones técnicas

- **Corte / relleno:** Δh = avance − natural. Δh < 0 ⇒ corte, Δh > 0 ⇒ relleno.
- **Área de píxel:** se asume CRS proyectado (metros). Para coordenadas
  geográficas (EPSG:4326), reproyectar antes a UTM o MAGNA-SIRGAS.
- **Reparto de volumen:** prorrateado por horas operativas reportadas.
- **Rendimiento:** `m³ / h` por equipo individual y para la flota completa.
