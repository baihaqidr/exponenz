@echo off
title EXPONENZ - Binance Futures Bot Dashboard
color 0A
echo =======================================================================
echo          EXPONENZ - QUANTITATIVE INTELLIGENCE HUB & BOT
echo       "The more you know, the more you see."
echo =======================================================================
echo.
echo [*] Memeriksa Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan di PATH! Pastikan Python sudah terinstall.
    pause
    exit /b
)

echo [*] Menjalankan Web Dashboard Server di http://localhost:5000 ...
echo [*] Browser akan terbuka otomatis dalam 1-2 detik...
echo.
echo Tekan [CTRL + C] di jendela ini kapan saja jika ingin mematikan server.
echo =======================================================================
echo.

python run_dashboard.py

pause
