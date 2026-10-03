@echo off
cd /d %~dp0

:: Python önbellek dosyalarını temizle (eski .pyc kalmasın)
if exist sahibinden_ai\__pycache__ rmdir /s /q sahibinden_ai\__pycache__
if exist sahibinden_ai\scraper\__pycache__ rmdir /s /q sahibinden_ai\scraper\__pycache__
if exist sahibinden_ai\analyzer\__pycache__ rmdir /s /q sahibinden_ai\analyzer\__pycache__

:: Sanal ortamın python'u ile ana modülü çalıştır
.\.venv\Scripts\python.exe -m sahibinden_ai.main

pause
