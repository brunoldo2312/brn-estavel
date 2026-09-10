@echo off
title Moeda Bruno v2 - Inicializador
cd /d "%~dp0"

echo ============================================================
echo       MOEDA BRUNO v2 - INICIALIZADOR
echo ============================================================
echo.

:: Configura o token do Ngrok via variavel de ambiente
:: Substitua pelo seu NOVO token (gere em dashboard.ngrok.com)
set "NGROK_AUTHTOKEN=COLE_SEU_NOVO_TOKEN_AQUI"

echo [1/2] Iniciando No + Explorador + GUI...
start "BRN v2 - No Principal" cmd /k "python main.py 6001"

timeout /t 4 /nobreak >nul

echo [2/2] Abrindo tunel publico com Ngrok (porta 8080)...
start "BRN v2 - Ngrok" cmd /k "ngrok http 8080"

echo.
echo ============================================================
echo  PRONTO! 
echo   - GUI:         http://127.0.0.1:8080
echo   - Painel Ngrok: http://127.0.0.1:4040
echo   - Link publico: copie da janela do Ngrok e cole no formulario
echo ============================================================
pause
