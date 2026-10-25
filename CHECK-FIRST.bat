@echo off
setlocal
chcp 65001 >nul
title DAG Orchestrator Desktop - Check
cd /d "%~dp0"
echo =====================================================
echo DAG Orchestrator Desktop v2.3 - Check
echo =====================================================
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1" -Mode Check
set "DAG_EXIT=%ERRORLEVEL%"
echo.
if not "%DAG_EXIT%"=="0" (
    echo ERROR: code %DAG_EXIT%. Please review the message above.
) else (
    echo Operation completed successfully.
)
echo.
pause
exit /b %DAG_EXIT%
