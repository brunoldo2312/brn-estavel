@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM ============================================================
REM  BRN-Estavel - Launcher unificado (Windows)
REM  Cria venv, instala dependencias e roda o programa
REM ============================================================

REM ----- CONFIGURACOES (edite se necessario) -----
set "PORT=6001"
set "MINER=brn1qxyzk7y0v2j4g0a8d9n5t3m2k7h4s6w8c9p2e"
set "MINE=--mine"
set "EXPLORER=--explorer"
set "OPEN_BROWSER=--open-browser"
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

REM ---- 4) Roda o programa ----
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

endlocal