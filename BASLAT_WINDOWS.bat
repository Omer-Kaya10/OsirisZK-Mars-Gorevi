@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 baslat.py
) else (
  python baslat.py
)
if errorlevel 1 (
  echo Python bulunamadi veya baslatilamadi. baslat.py dosyasini Python IDLE ile acin.
  pause
)
