@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 mars_oyunu.py
) else (
    python mars_oyunu.py
)
if errorlevel 1 (
    echo.
    echo Bir hata oldu. Python 3.10+ yüklü mü kontrol edin.
    pause
)
