@echo off
setlocal EnableDelayedExpansion

REM ========================================================
REM  Script de instalacao e execucao do projeto BRN-L2
REM  Usa Miniconda + conda-forge (sem canais defaults)
REM  Instala TODAS as dependencias via conda para evitar
REM  a necessidade do Microsoft Visual C++ Build Tools.
REM ========================================================

echo ========================================================
echo  BRN-L2 - Instalacao e Execucao
echo ========================================================
echo.

REM --------------------------------------------------------
REM  1. Verificar se o Conda esta instalado
REM --------------------------------------------------------
echo [INFO] Verificando a presenca do Conda...

where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Conda encontrado no PATH.
    set "CONDA_FOUND=1"
    goto :conda_found
)

if exist "%UserProfile%\miniconda3\Scripts\conda.exe" (
    echo [INFO] Miniconda encontrado em %UserProfile%\miniconda3
    set "CONDA_PATH=%UserProfile%\miniconda3"
    set "CONDA_FOUND=1"
    goto :conda_found
)

if exist "%UserProfile%\Miniconda3\Scripts\conda.exe" (
    echo [INFO] Miniconda encontrado em %UserProfile%\Miniconda3
    set "CONDA_PATH=%UserProfile%\Miniconda3"
    set "CONDA_FOUND=1"
    goto :conda_found
)

if exist "C:\ProgramData\miniconda3\Scripts\conda.exe" (
    echo [INFO] Miniconda encontrado em C:\ProgramData\miniconda3
    set "CONDA_PATH=C:\ProgramData\miniconda3"
    set "CONDA_FOUND=1"
    goto :conda_found
)

echo [AVISO] Miniconda nao foi encontrado.
echo [INFO] Iniciando a instalacao automatica do Miniconda...

REM --------------------------------------------------------
REM  2. Instalar Miniconda automaticamente
REM --------------------------------------------------------
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
echo.

REM --------------------------------------------------------
REM  3. Inicializar o Conda no ambiente atual
REM --------------------------------------------------------
call "%CONDA_PATH%\Scripts\activate.bat" "%CONDA_PATH%"

REM --------------------------------------------------------
REM  4. Aceitar automaticamente os Termos de Servico
REM     (fallback caso os canais defaults ainda sejam usados)
REM --------------------------------------------------------
echo [INFO] Configurando aceitacao automatica dos Termos de Servico...
set CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes

REM --------------------------------------------------------
REM  5. Remover o canal "defaults" da instalacao raiz
REM     (isso evita o erro de ToS da Anaconda)
REM --------------------------------------------------------
echo [INFO] Removendo canal "defaults" do .condarc da instalacao raiz...

if exist "%CONDA_PATH%\.condarc" (
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels defaults >nul 2>&1
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels https://repo.anaconda.com/pkgs/main >nul 2>&1
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels https://repo.anaconda.com/pkgs/r >nul 2>&1
    call conda config --file "%CONDA_PATH%\.condarc" --remove channels https://repo.anaconda.com/pkgs/msys2 >nul 2>&1
)

REM --------------------------------------------------------
REM  6. Configurar conda-forge como unico canal
REM --------------------------------------------------------
echo [INFO] Configurando o Conda para usar apenas o canal conda-forge...

call conda config --remove-key channels >nul 2>&1
call conda config --add channels conda-forge
call conda config --set channel_priority strict

echo [INFO] Canais configurados:
call conda config --show channels
echo.

REM --------------------------------------------------------
REM  7. Criar ambiente com Python 3.13
REM --------------------------------------------------------
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
echo.

REM --------------------------------------------------------
REM  8. Instalar TODAS as dependencias via conda-forge
REM     (evita compilacao C++ e o erro do Build Tools)
REM --------------------------------------------------------
echo [INFO] Instalando TODAS as dependencias via conda-forge...
echo [INFO] Isso pode levar alguns minutos na primeira vez.
echo.

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
    echo.
    echo [AVISO] A instalacao em lote falhou. Tentando pacote por pacote...
    echo.

    call conda install -n brn-l2 --override-channels -c conda-forge -y coincurve
    call conda install -n brn-l2 --override-channels -c conda-forge -y ckzg
    call conda install -n brn-l2 --override-channels -c conda-forge -y lru-dict
    call conda install -n brn-l2 --override-channels -c conda-forge -y orjson
    call conda install -n brn-l2 --override-channels -c conda-forge -y web3
    call conda install -n brn-l2 --override-channels -c conda-forge -y eth-account
    call conda install -n brn-l2 --override-channels -c conda-forge -y eth-keys
    call conda install -n brn-l2 --override-channels -c conda-forge -y eth-utils
    call conda install -n brn-l2 --override-channels -c conda-forge -y requests
    call conda install -n brn-l2 --override-channels -c conda-forge -y colorama
    call conda install -n brn-l2 --override-channels -c conda-forge -y python-dotenv
    call conda install -n brn-l2 --override-channels -c conda-forge -y loguru
)

echo.
echo [INFO] Dependencias instaladas com sucesso via conda.
echo.

REM --------------------------------------------------------
REM  9. Ativar ambiente e verificar pacotes
REM --------------------------------------------------------
echo [INFO] Ativando ambiente brn-l2...
call conda activate brn-l2

echo [INFO] Confirmando a versao do Python dentro do ambiente...
python --version
echo.

echo [INFO] Verificando pacotes criticos...
python -c "import orjson; print('  [OK] orjson')" 2>nul || echo [AVISO] orjson nao encontrado
python -c "import web3; print('  [OK] web3')" 2>nul || echo [AVISO] web3 nao encontrado
python -c "import coincurve; print('  [OK] coincurve')" 2>nul || echo [AVISO] coincurve nao encontrado
python -c "import ckzg; print('  [OK] ckzg')" 2>nul || echo [AVISO] ckzg nao encontrado
python -c "import lru; print('  [OK] lru-dict')" 2>nul || echo [AVISO] lru-dict nao encontrado
python -c "import eth_account; print('  [OK] eth-account')" 2>nul || echo [AVISO] eth-account nao encontrado
echo.

REM --------------------------------------------------------
REM  10. Executar o projeto
REM --------------------------------------------------------
if exist "node.py" (
    echo [INFO] Executando o projeto...
    echo.
    python node.py
) else (
    echo [ERRO] Arquivo node.py nao encontrado no diretorio atual.
    echo [INFO] Certifique-se de que o run.bat esta na pasta raiz do projeto.
)

echo.
echo ========================================================
echo  Processo finalizado.
echo ========================================================
pause >nul
endlocal