📘 Manual de Instalação e Execução — BRN Blockchain
Guia passo a passo para instalar as dependências criptográficas e executar o sistema BRN-Estavel / Bruno Blockchain Real.

📋 Pré-requisitos
Antes de começar, certifique-se de ter instalado:

Software	Versão mínima	Download
Python	3.9 ou superior	https://www.python.org/downloads/
Git	Qualquer	https://git-scm.com/download/win
⚠️ Na instalação do Python, marque a opção "Add Python to PATH".

Para conferir se está tudo certo, abra o CMD e rode:

cmd
python --version
git --version
📁 Passo 1 — Acessar a pasta do projeto
cmd
cd C:\Users\mayra\OneDrive\Imagens\bruno crypto\brn
Se a pasta ainda não existir, clone o repositório:

cmd
git clone https://github.com/brunoldo2312/brn-estavel.git
cd brn-estavel
🐍 Passo 2 — Criar e ativar o ambiente virtual (venv)
O ambiente virtual isola as dependências do projeto, evitando conflitos com outros programas Python.

Criar o venv (só na primeira vez):

cmd
python -m venv venv
Ativar o venv (sempre que for usar o projeto):

cmd
venv\Scripts\activate
Quando ativado, o prompt exibirá (venv) no início:

text
(venv) C:\Users\mayra\OneDrive\Imagens\bruno crypto\brn>
💡 Para sair do venv depois, basta digitar: deactivate

🔐 Passo 3 — Instalar as dependências criptográficas
Essas são as bibliotecas essenciais para o funcionamento do sistema:

3.1 — Atualizar o pip (recomendado)
cmd
python -m pip install --upgrade pip
3.2 — Instalar as bibliotecas criptográficas e de interface
cmd
pip install ecdsa
pip install pywebview
Descrição de cada uma:

Biblioteca	Função
ecdsa	Gera chaves privadas/públicas na curva secp256k1 (mesma do Bitcoin) e valida assinaturas digitais
pywebview	Cria a janela desktop que exibe a interface web do sistema
3.3 — Instalar dependências auxiliares (recomendado)
Estas costumam ser usadas em projetos de blockchain com interface web:

cmd
pip install requests
pip install flask
pip install base58
pip install bech32
pip install qrcode[pil]
Biblioteca	Função
requests	Comunicação HTTP com nós Bitcoin (RPC)
flask	Servidor web local da interface
base58	Codificação de endereços Bitcoin (formato legado)
bech32	Codificação de endereços SegWit (bc1...)
qrcode[pil]	Geração de QR Codes para os endereços
3.4 — Instalação em lote (alternativa rápida)
Se preferir instalar tudo de uma só vez:

cmd
pip install ecdsa pywebview requests flask base58 bech32 qrcode[pil]
📄 Passo 4 — Criar o arquivo requirements.txt
Para não precisar lembrar dos comandos no futuro, registre as dependências:

cmd
echo ecdsa> requirements.txt
echo pywebview>> requirements.txt
echo requests>> requirements.txt
echo flask>> requirements.txt
echo base58>> requirements.txt
echo bech32>> requirements.txt
echo qrcode[pil]>> requirements.txt
Conferir o conteúdo:

cmd
type requirements.txt
Nas próximas vezes, basta rodar:

cmd
pip install -r requirements.txt
▶️ Passo 5 — Executar o sistema
Com o (venv) ativado e as dependências instaladas:

cmd
py bruno_blockchain_real.py 6002
🔢 O número 6002 é a porta onde a interface web será servida. Se estiver ocupada, troque por outra (ex: 6003, 8080).

O sistema deverá:

Abrir uma janela desktop com a interface, ou

Disponibilizar a interface em http://localhost:6002 no navegador.

🔁 Rotina para rodar novamente (resumo)
Toda vez que quiser executar o sistema, faça apenas:

cmd
cd C:\Users\mayra\OneDrive\Imagens\bruno crypto\brn
venv\Scripts\activate
py bruno_blockchain_real.py 6002
🛠️ Solução de problemas comuns
Erro	Causa	Solução
No module named 'webview'	pywebview não instalado	pip install pywebview
No module named 'ecdsa'	ecdsa não instalado	pip install ecdsa
No module named 'flask'	flask não instalado	pip install flask
No module named 'requests'	requests não instalado	pip install requests
No module named 'base58'	base58 não instalado	pip install base58
venv\Scripts\activate não é reconhecido	venv não foi criado	python -m venv venv
pip não é reconhecido	Python fora do PATH	Reinstale o Python marcando "Add to PATH"
Porta 6002 em uso	Outro processo usa a porta	Use outra porta: py bruno_blockchain_real.py 6003
🔒 Boas práticas de segurança
Nunca suba o venv/ nem o wallet.json para o GitHub.

Crie um arquivo .gitignore com:

cmd
echo venv/>> .gitignore
echo wallet.json>> .gitignore
echo __pycache__/>> .gitignore
Guarde a chave privada da carteira em local seguro (nunca compartilhe).

Faça backup periódico do arquivo wallet.json e do ledger.json.

📌 Ordem resumida (cheat sheet)
cmd
:: 1. Entrar na pasta
cd C:\Users\mayra\OneDrive\Imagens\bruno crypto\brn

:: 2. Ativar ambiente virtual
venv\Scripts\activate

:: 3. Instalar dependências criptográficas
pip install ecdsa pywebview requests flask base58 bech32 qrcode[pil]

:: 4. Executar o sistema
py bruno_blockchain_real.py 6002
