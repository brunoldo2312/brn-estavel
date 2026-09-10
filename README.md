Manual da Carteira BRN

Instalação, recebimento, transferências e testes entre computadores

Este manual explica como executar a carteira BRN, criar e proteger carteiras, receber e enviar BRN, minerar blocos e demonstrar uma transferência entre dois computadores na mesma rede. A BRN é um protótipo educacional: não use valores reais, senhas reutilizadas ou chaves privadas de outras carteiras.

Visão geral

A carteira BRN guarda um endereço público para receber BRN e uma chave privada para autorizar envios. As transferências entram na mempool e são confirmadas quando um bloco é minerado. O extrato mostra depósitos, retiradas, recompensas de mineração e operações pendentes.

Item

Finalidade

Endereço BRN

Pode ser compartilhado para receber depósitos.

Chave privada

Autoriza gastos. Nunca compartilhe.

Mempool

Fila temporária de transações antes da confirmação.

Bloco confirmado

Registro persistente da transação na blockchain.

1 Preparação no primeiro computador

Extraia o projeto em uma pasta local. Evite executar diretamente dentro de uma pasta sincronizada enquanto o aplicativo estiver aberto, pois o serviço de sincronização pode manter arquivos bloqueados.

Abra o Prompt de Comando na pasta do projeto e execute:

py -m venv env

env\Scripts\activate

python -m pip install --upgrade pip

pip install ecdsa cryptography pywebview PyQt6 PyQt6-WebEngine

python bruno_blockchain_real.py 6001

A janela da carteira deve abrir. A porta 6001 identifica o primeiro nó da rede local.

2 Criar ou importar uma carteira

Clique em Criar Nova Carteira ECDSA.

Anote o endereço público. Ele começa com brn1 e é usado para receber BRN.

Guarde a chave privada em local seguro. Ela permite movimentar o saldo.

Para manter um backup, escolha um nome de arquivo, use senha de pelo menos 12 caracteres e clique em Exportar e Criptografar Backup.

Para importar uma carteira existente, informe o nome do arquivo e a senha e clique em Importar e Descriptografar.

3 Receber depósitos

Crie ou importe a carteira que receberá BRN.

Abaixo de Seu Endereço Público, clique em Copiar endereço de recebimento.

Envie apenas o endereço copiado para a pessoa ou carteira que fará o depósito.

Após a confirmação do bloco, verifique o saldo e o extrato de Depósitos e Retiradas.

Importante: o botão copia somente o endereço público. Não envie a chave privada, mesmo para suporte técnico ou outro participante da rede.

4 Enviar BRN e confirmar a retirada

Carregue a carteira que possui saldo; a chave privada e a chave pública precisam estar disponíveis na tela.

No campo de destino, cole o endereço BRN de recebimento do destinatário.

Informe a quantia e clique em Assinar e Enviar Transação.

Inicie a mineração ou aguarde um minerador da rede confirmar a operação em um novo bloco.

Consulte o extrato. Antes do bloco, a retirada aparece como Pendente; depois, como Confirmada.

A carteira recusa quantias inválidas, falta de saldo, duplicidade de operação pendente e tentativas de usar uma chave que não corresponda ao endereço remetente.

5 Minerar blocos

Clique em Iniciar Mineração Contínua para minerar em segundo plano. A carteira usada na mineração recebe a recompensa de bloco. Clique novamente para parar. A mineração é apenas parte da demonstração local e pode consumir processamento do computador.

6 Demonstração entre dois computadores

Os dois computadores devem estar conectados à mesma rede Wi-Fi ou cabo e usar a mesma versão do projeto.

Etapa

Ação

Computador A

Execute python bruno_blockchain_real.py 6001, crie a carteira A e mine BRN nela.

Computador B

Instale o projeto e execute python bruno_blockchain_real.py 6002. Crie a carteira B e copie seu endereço de recebimento.

Obter o IP do A

No CMD do computador A, execute ipconfig e anote o Endereço IPv4, por exemplo 192.168.0.17.

Sincronizar o B

Na carteira B, informe o IP do A e a porta 6001 em Conectar e Sincronizar Cadeia.

Enviar e confirmar

No A, envie BRN para o endereço B e mine um bloco. No B, sincronize novamente para visualizar o depósito.

Se a conexão falhar, libere a porta 6001 no computador A. Em CMD aberto como administrador: netsh advfirewall firewall add rule name="BRN Porta 6001" dir=in action=allow protocol=TCP localport=6001

7 Verificação da demonstração

No computador A, o extrato deve mostrar a retirada confirmada.

No computador B, o extrato deve mostrar o depósito confirmado.

Os dois nós devem exibir a mesma quantidade de blocos após a sincronização.

Registre endereço de origem, endereço de destino, valor, data e identificador mostrado no extrato para apresentar a prova.

8 Solução de problemas

Situação

Como resolver

ModuleNotFoundError core

Use a pasta do projeto atualizado. A primeira linha de bruno_blockchain_real.py deve ser import hashlib.

Porta em uso

Feche outra instância do programa ou inicie usando outra porta, como 6002.

Saldo não aparece no outro PC

Confirme que o bloco foi minerado e sincronize novamente a carteira que recebeu.

Botão de cópia não aparece

Feche e abra a carteira usando a versão que contém o index.html atualizado.

Senha de backup recusada

Use uma senha com no mínimo 12 caracteres para novos backups.

9 Cuidados de segurança

Nunca compartilhe a chave privada, a senha do backup ou o arquivo de carteira descriptografado.

Use esta aplicação apenas para aprendizado, demonstrações e BRN de teste.

Mantenha cópias criptografadas do backup em local protegido.

Não exponha as portas da carteira à internet sem compreender o risco e configurar firewall adequadamente.

Manual da Carteira BRN | Uso educacional e testes em rede local
