@echo off
setlocal

REM ========================================================
REM  Script de instalacao e execucao do projeto BRN-L2
REM  Usa Miniconda + conda-forge para evitar compilacao C++
REM ========================================================

echo [INFO] Verificando a presenca do Conda...

where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Conda encontrado no PATH.
    goto :conda_found
)

if exist "%UserProfile%\miniconda3\Scripts\conda.exe" (
    echo [INFO] Miniconda encontrado em %UserProfile%\miniconda3
    set "CONDA_PATH=%UserProfile%\miniconda3"
    goto :conda_found
)

if exist "%UserProfile%\Miniconda3\Scripts\conda.exe" (
    echo [INFO] Miniconda encontrado em %UserProfile%\Miniconda3
    set "CONDA_PATH=%UserProfile%\Miniconda3"
    goto :conda_found
)

if exist "C:\ProgramData\miniconda3\Scripts\conda.exe" (
    echo [INFO] Miniconda encontrado em C:\ProgramData\miniconda3
    set "CONDA_PATH=C:\ProgramData\miniconda3"
    goto :conda_found
)

echo [AVISO] Miniconda nao foi encontrado.
echo [INFO] Iniciando a instalacao automatica do Miniconda...

set "MINICONDA_INSTALLER=%TEMP%\Miniconda3-latest-Windows-x86_64.exe"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"

echo [INFO] Baixando o Miniconda...
powershell -Command "& {Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile '%MINICONDA_INSTALLER%'}"
if not exist "%MINICONDA_INSTALLER%" (
    echo [ERRO] Falha ao baixar o instalador do Miniconda.
    pause
    exit /b 1
)

echo [INFO] Instalando o Miniconda silenciosamente...
start /wait "" "%MINICONDA_INSTALLER%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%UserProfile%\miniconda3
if %errorlevel% neq 0 (
    echo [ERRO] A instalacao do Miniconda falhou.
    pause
    exit /b 1
)

set "CONDA_PATH=%UserProfile%\miniconda3"
echo [INFO] Miniconda instalado com sucesso.

:conda_found
if not defined CONDA_PATH (
    for /f "tokens=*" %%i in ('where conda 2^>nul') do (
        set "CONDA_PATH=%%~dpi.."
        goto :conda_path_set
    )
)
:conda_path_set

echo [INFO] Usando o Miniconda para configurar o ambiente.

call "%CONDA_PATH%\Scripts\activate.bat" "%CONDA_PATH%"

REM ========================================================
REM  PASSO 1: Aceitar automaticamente os ToS da Anaconda
REM ========================================================
echo [INFO] Configurando aceitacao automatica dos Termos de Servico...
set CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes

REM ========================================================
REM  PASSO 2: Remover "defaults" do .condarc DA INSTALACAO RAIZ
REM ========================================================
echo [INFO] Removendo canal "defaults" do .condarc da instalacao raiz...

if exist "%CONDA_PATH%\.condarc" (
    echo [INFO] Arquivo .condarc da raiz encontrado. Removendo defaults...
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels defaults >nul 2>&1
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels https://repo.anaconda.com/pkgs/main >nul 2>&1
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels https://repo.anaconda.com/pkgs/r >nul 2>&1
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels https://repo.anaconda.com/pkgs/msys2 >nul 2>&1
)

REM ========================================================
REM  PASSO 3: Configurar conda-forge como unico canal
REM ========================================================
echo [INFO] Configurando o Conda para usar apenas o canal conda-forge...

call conda config --remove-key channels >nul 2>&1
call conda config --add channels conda-forge
call conda config --set channel_priority strict

echo [INFO] Canais configurados (usuario):
call conda config --show channels
echo.

REM ========================================================
REM  PASSO 4: Criar ambiente com Python 3.13
REM ========================================================
echo [INFO] Removendo ambiente antigo (se existir)...
call conda env remove -n brn-l2 -y >nul 2>&1

echo [INFO] Criando novo ambiente com Python 3.13...
call conda create -n brn-l2 python=3.13 --override-channels -c conda-forge -y
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar o ambiente conda.
    pause
    exit /b 1
)

echo [INFO] Ambiente brn-l2 criado com sucesso.

REM ========================================================
REM  PASSO 5: Instalar TODAS as dependencias via CONDA
REM  (evita compilacao C++ e o erro do Visual C++ Build Tools)
REM ========================================================
echo [INFO] Instalando todas as dependencias via conda-forge...
echo [INFO] (Isso pode levar alguns minutos na primeira vez)

call conda install -n brn-l2 --override-channels -c conda-forge -y ^
    coincurve ^
    ckzg ^
    lru-dict ^
    orjson ^
    web3 ^
    eth-account ^
    eth-keys ^
    eth-utils ^
    requests ^
    colorama ^
    python-dotenv ^
    loguru

if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias via conda.
    echo [INFO] Tentando instalar pacotes individualmente para identificar o problema...
    call conda install -n brn-l2 --override-channels -c conda-forge -y coincurve
    call conda install -n brn-l2 --override-channels -c conda-forge -y ckzg
    call conda install -n brn-l2 --override-channels -c conda-forge -y lru-dict
    call conda install -n brn-l2 --override-channels -c conda-forge -y orjson
    call conda install -n brn-l2 --override-channels -c conda-forge -y web3 eth-account eth-keys eth-utils
    call conda install -n brn-l2 --override-channels -c conda-forge -y requests colorama python-dotenv loguru
)

echo [INFO] Dependencias instaladas com sucesso via conda.

REM ========================================================
REM  PASSO 6: Ativar ambiente e verificar
REM ========================================================
echo [INFO] Ativando ambiente brn-l2...
call conda activate brn-l2

echo [INFO] Confirmando a versao do Python dentro do ambiente...
python --version

echo [INFO] Verificando pacotes instalados...
python -c "import orjson; print('orjson OK')" 2>nul || echo [AVISO] orjson nao encontrado
python -c "import web3; print('web3 OK')" 2>nul || echo [AVISO] web3 nao encontrado
python -c "import coincurve; print('coincurve OK')" 2>nul || echo [AVISO] coincurve nao encontrado

REM ========================================================
REM  PASSO 7: Executar o projeto
REM ========================================================
echo [INFO] Executando o projeto...
python node.py

echo.
echo [INFO] Processo finalizado. Pressione qualquer tecla para sair.
pause >nul
endlocal