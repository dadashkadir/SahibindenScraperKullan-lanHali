@echo off
REM SahibindenScraper - tek dosyalı exe üretir (konsol penceresi AÇIK olmalı: parametreler soruluyor)
cd /d "%~dp0"

python -m venv .venv 2>nul
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --onefile --console --noconfirm --clean ^
  --name SahibindenScraper ^
  --add-data "sahibinden_ai\storage\fonts;sahibinden_ai\storage\fonts" ^
  --collect-all playwright ^
  sahibinden_ai\main.py

echo.
echo Cikti: %~dp0dist\SahibindenScraper.exe
pause
