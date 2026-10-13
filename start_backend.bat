@echo off
echo ===================================================
echo Starting Studio Desire - Python FastAPI Backend
echo Port: 8000 ^| Swagger Docs: http://localhost:8000/docs
echo ===================================================
cd backend
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)
