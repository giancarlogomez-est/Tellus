"""Atajo: ejecuta el pipeline real (03_pipeline_diario/pipeline.py).

Antes había aquí una copia completa que se había desincronizado de la que usa
la interfaz. Ahora hay una sola implementación.

    python pipeline.py --fecha 2026-10-28 --mensual
"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).parent / "03_pipeline_diario" / "pipeline.py"),
                   run_name="__main__")
