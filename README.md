💼 Moeda Bruno (BRN) - Carteira Avançada & Blockchain P2P
A Moeda Bruno (BRN) é uma implementação experimental de um ecossistema de criptomoeda descentralizado baseado em princípios acadêmicos do protocolo CryptoNote/Monero . O projeto apresenta uma arquitetura modular com um livro-razão imutável, sincronização independente de nós Peer-to-Peer (P2P), transmissão de transações via Mempool Broadcast e um utilitário automático de redirecionamento de portas (UPnP).

🚀 Funcionalidades e Diferenciais Acadêmicos
Automação de Rede (UPnP): Descoberta e mapeamento automático de portas de entrada diretamente no roteador doméstico via pacotes SSDP.
Consenso de Cadeia Maior ( Longest Chain Rule ): Algoritmo de resolução de consenso que substitui atomicamente uma cadeia local se um par remoto apresenta uma blockchain rígida mais longa e válida.
Mempool Gossip Protocol: Propagação atômica em segundo plano de novas transações para todas as máquinas parceiras conectadas à rede antes da mineração do bloco.
Livro-Razão Relacional (SQLite3): Persistência imutável indexada com auditorias históricas e reconstituição dinâmica de saldos em tempo real.
Backup Criptografado de Chaves (.wallet): Cifragem simétrica em fluxo utilizando derivação de chaves PBKDF de 5000 rodadas para proteção de Spend Keys locais.
Interface Gráfica Nativa (Desktop Puro): Janela escura desacoplada construída sobre a ponte de injeção JavaScript-Python ( pywebview+ PyQt6).
📁 Estrutura Modular do Projeto
O ecossistema foi dividido em módulos isolados para garantir a consistência de dados, mitigar erros de tokenização e melhorar o tempo de compilação:

├── bruno_blockchain_real.py  # Motor principal, API de controle e chamadas P2P
├── cripto_db.py              # Camada de persistência relacional e queries ordinais SQLite3
├── cripto_wallet.py          # Gerenciador de backup e criptografia PBKDF simétrica
├── cripto_p2p_network.py     # Descoberta de Gateway e Auto Port Forwarding (UPnP)
└── index.html                # Interface visual baseada na ponte Javascript-Python Native
🛠️ Como Executar o Projeto (Máquina Local)
1. Preparação do Ambiente e Dependências (Linux Ubuntu)
Abra o terminal no diretório do projeto e execute os comandos para instalar as bibliotecas do sistema e isolar o ambiente virtual:

# Instalar pacotes de sistema necessários
sudo apt update && sudo apt install python3-venv python3-full python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 -y

# Criar e ativar o ambiente virtual (VENV)
python3 -m venv env
source env/bin/activate

# Instalar dependências de execução e o motor gráfico isolado PyQt6
pip install --upgrade pip
pip install pywebview flask pyqt6 PyQt6-WebEngine qtpy
2. Inicialização do Nó Principal
Sempre limpe os bancos de dados corrompidos ou inconsistentes de sessões anteriores antes de iniciar ou nó na porta de sua escolha (Ex: 6001):

rm -rf __pycache__
rm -f *.db
python3 bruno_blockchain_real.py 6001
🌐 Sincronização entre Máquinas Físicas Diferentes
Para rodar a Moeda Bruno em múltiplos computadores conectados na mesma rede Wi-Fi ou cabo:

1. identificar o IP da Máquina Principal
No terminal do seu nó principal (Ex: Seu HP Pavilion), execute:

hostname -I
# Retornará algo como: 192.168.0.17
2. Executar o Nó na Segunda Máquina
Copie os arquivos do projeto para o segundo computador. Abra o terminal dele e inicie o script alterando a porta de escuta para não gerar conflitos:

Sem Linux: python3 bruno_blockchain_real.py 6002
Sem Windows (Administrador CMD):
python -m venv env
.\env\Scripts\activate
pip install pywebview flask pyqt6 PyQt6-WebEngine qtpy
python bruno_blockchain_real.py 6002
3. Sincronizar as Cadeias de Blocos
Vá até a tela do aplicativo na Segunda Máquina .
No painel superior rosa ( Rede Descentralizada ), insira o IP do seu nó principal: 192.168.0.17.
Defina a porta remota do nó principal: 6001.
Clique em "Conectar e Sincronizar Cadeira" . O ecossistema fará com que o download e a verificação criptográfica do livro-razão sejam feitos automaticamente.
Nota de Firewall: Se a conexão falhar, certifique-se de liberar a porta de entrada no terminal do nó Linux principal rodando: sudo ufw allow 6001/tcp.

📦 Como Gerar o Executável Binário (.App / .Exe)
Para distribuir a carteira de privacidade como um aplicativo desktop nativo e independente (sem a necessidade de instalação prévia do Python na máquina de destino):

No Linux (geração binária nova nativa)
pip install pyinstaller
pyinstaller --onefile --add-data "index.html:." --windowed bruno_blockchain_real.py

# Para executar o binário gerado na pasta dist/
cd dist
chmod +x bruno_blockchain_real
./bruno_blockchain_real 6001
No Windows (Gera o arquivo correspondente .exe)
Abra o Prompt de Comando (CMD) do Windows dentro da pasta do projeto e execute:

pip install pyinstaller
pyinstaller --onefile --add-data "index.html;." --windowed bruno_blockchain_real.py
O arquivo unificado estará disponível no diretório dist/bruno_blockchain_real.exe.
