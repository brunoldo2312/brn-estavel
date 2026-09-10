@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM ============================================================
REM  BRN-Estavel - Launcher unificado (Windows)
REM  Cria venv, instala dependencias, configura Ngrok e roda
REM ============================================================

REM ----- CONFIGURACOES (edite se necessario) -----
set "PORT=6001"
set "EXPLORER_PORT=8080"
set "MINER=brn1qxyzk7y0v2j4g0a8d9n5t3m2k7h4s6w8c9p2e"
set "MINE=--mine"
set "EXPLORER=--explorer"
set "OPEN_BROWSER=--open-browser"

REM ----- TOKEN NGROK -----
set "NGROK_AUTHTOKEN=ep_3J92eYaKL7KqlZfSSoIyuDNrewF"
REM -----------------------------------------------

REM ---- 1) Verifica Python ----
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo        Instale o Python 3.10+ em https://www.python.org/downloads/
    echo        Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

REM ---- 2) Cria o venv se nao existir ----
if not exist "env\Scripts\python.exe" (
    echo [SETUP] Criando ambiente virtual...
    python -m venv env
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o venv.
        pause
        exit /b 1
    )
    set "NEED_INSTALL=1"
) else (
    set "NEED_INSTALL=0"
)

REM ---- 3) Instala dependencias se necessario ----
if "!NEED_INSTALL!"=="1" (
    echo [SETUP] Instalando dependencias...
    call "env\Scripts\python.exe" -m pip install --upgrade pip
    if exist "requirements.txt" (
        call "env\Scripts\python.exe" -m pip install -r requirements.txt
    ) else (
        call "env\Scripts\python.exe" -m pip install ^
            coincurve^>=19.0.0 ^
            orjson^>=3.9 ^
            flask^>=3.0 ^
            cryptography^>=42.0
    )
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
    echo [SETUP] Dependencias instaladas.
)

REM ---- 4) Verifica e configura Ngrok ----
where ngrok >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Ngrok nao encontrado no PATH.
    echo         O explorador rodara apenas localmente em http://localhost:%EXPLORER_PORT%
    echo         Para expor publicamente, instale o Ngrok: https://ngrok.com/download
    set "NGROK_OK=0"
) else (
    echo [NGROK] Configurando authtoken...
    ngrok config add-authtoken %NGROK_AUTHTOKEN% >nul 2>&1
    if errorlevel 1 (
        echo [AVISO] Falha ao configurar o token. Túnel publico desabilitado.
        set "NGROK_OK=0"
    ) else (
        echo [NGROK] Token configurado.
        set "NGROK_OK=1"
    )
)

REM ---- 5) Sobe o tunnel Ngrok (se disponivel) ----
set "NGROK_PID="
if "!NGROK_OK!"=="1" (
    echo [NGROK] Abrindo tunel publico para a porta %EXPLORER_PORT%...
    start "BRN-Ngrok" /min cmd /c "ngrok http %EXPLORER_PORT% --log=stdout > ngrok.log 2>&1"
    timeout /t 3 /nobreak >nul
    echo [NGROK] URL publica disponivel em http://127.0.0.1:4040
)

REM ---- 6) Roda o programa ----
echo [RUN] Iniciando BRN-Estavel na porta %PORT% ...
call "env\Scripts\python.exe" main.py ^
    --port %PORT% ^
    --miner "%MINER%" ^
    %MINE% %EXPLORER% %OPEN_BROWSER%

if errorlevel 1 (
    echo.
    echo [ERRO] O programa encerrou com erro.
    pause
    exit /b 1
)

REM ---- 7) Limpa processos Ngrok ao sair ----
taskkill /FI "WINDOWTITLE eq BRN-Ngrok" /F >nul 2>&1

endlocal