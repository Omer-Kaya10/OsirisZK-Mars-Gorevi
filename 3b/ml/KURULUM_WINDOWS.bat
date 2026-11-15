@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/4] Sanal ortam (.venv) olusturuluyor...
py -3 -m venv .venv 2>nul || python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo [2/4] Klasik ML paketleri...
pip install -r requirements.txt
echo [3/4] Derin ogrenme (PyTorch) - birkac dakika surebilir...
pip install -r requirements-dl.txt
echo [4/4] Duman testi (sentetik veriyle tum boru hatti)...
python tests\run_smoke_test.py
echo.
echo Kurulum tamam. Komutlar icin README_ML.md dosyasina bakin.
pause
