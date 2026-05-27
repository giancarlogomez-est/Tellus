@echo off
REM Lanzador del dashboard Mensure v2.0
cd /d "%~dp0"
streamlit run src\frontend\dashboard.py
