@echo off
echo.
echo  ================================
echo   NeuralApply - AI Job Agent
echo  ================================
echo.

cd /d "%~dp0backend"

if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads

echo  Starting server at http://localhost:8000
echo  Press Ctrl+C to stop.
echo.

uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
