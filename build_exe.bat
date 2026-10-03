@echo off
REM Build script for Sahibinden AI Scraper executable
REM Requires PyInstaller installed in the current environment (pip install pyinstaller)

echo Building executable with PyInstaller...
pyinstaller --onefile --name SahibindenAI ^
    --add-data "sahibinden_ai;./sahibinden_ai" ^
    --hidden-import=playwright.async_api ^
    --hidden-import=playwright._impl._api_structures ^
    --hidden-import=pandas ^
    --hidden-import=numpy ^
    --hidden-import=fpdf ^
    sahibinden_ai/main.py

echo.
echo Build completed. Executable is in dist\SahibindenAI.exe
pause