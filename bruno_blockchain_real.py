import hashlib
import time
import json
import sqlite3
import secrets
import socket
import threading
import sys
from decimal import Decimal, InvalidOperation
import webview
from cripto_wallet import WalletManager
from cripto_db import BlockchainDB
from cripto_p2p_network import AutoPortForwarder


def _harden_console_encoding():
    """Evita que emojis nos logs derrubem threads em consoles Windows (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass


_harden_console_encoding()

COIN_NAME = "Bruno"
COIN_SYMBOL = "BRN"
BLOCK_REWARD = 1.0
GENESIS_ADDRESS = "brn1111cd943fa71e1f91dcd62f52fc6138bc845ab"
GENESIS_AMOUNT = 100000.0
DIFFICULTY_ADJUSTMENT_INTERVAL = 5  # Ajusta a cada 5 blocos
TARGET_BLOCK_TIME = 10.0  # Tempo ideal por bloco em segundos
MAX_DIFFICULTY = 8
MAX_BLOCK_TRANSACTIONS = 1_000
MAX_FUTURE_SECONDS = 120
MONERO_FORK_NETWORK_ID = [0xAA, 0xBB, 0xCC, 0xDD, 0x11, 0x22, 0x33, 0x44]

BOOTSTRAP_PEERS_FILE = "bootstrap_peers.json"
DEFAULT_BOOTSTRAP_PEERS = [
    ("192.168.0.17", 6001)
]


def _load_bootstrap_peers():
    """Carrega nós iniciais de bootstrap_peers.json (se existir).

    Permite apontar para um nó com IP público em outra região sem editar o
    código. Formato esperado: [{"ip": "1.2.3.4", "port": 6001}, ...].
    """
    try:
        with open(BOOTSTRAP_PEERS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        peers = [(str(item["ip"]).strip(), int(item["port"])) for item in raw]
        peers = [(ip, port) for ip, port in peers if ip]
        return peers or list(DEFAULT_BOOTSTRAP_PEERS)
    except (OSError, ValueError, KeyError, TypeError):
        return list(DEFAULT_BOOTSTRAP_PEERS)


BOOTSTRAP_PEERS = _load_bootstrap_peers()

class BrunoBlock:
    def __init__(self, index, previous_hash, transactions, difficulty=4, nonce=0, timestamp=None, block_hash=None):
        self.index = int(index)
        self.timestamp = float(timestamp) if timestamp is not None else time.time()
        self.previous_hash = str(previous_hash)
        self.transactions = transactions if isinstance(transactions, list) else json.loads(transactions)
        self.difficulty = int(difficulty)
        self.nonce = int(nonce)
        self.network_id = MONERO_FORK_NETWORK_ID
        self.hash = str(block_hash) if block_hash else self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index, "timestamp": self.timestamp, "previous_hash": self.previous_hash,
            "transactions": self.transactions, "difficulty": self.difficulty, "nonce": self.nonce, "network_id": self.network_id
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self, stop_event=None):
        target = "0" * self.difficulty
        while self.hash[:self.difficulty] != target:
            if stop_event and stop_event.is_set():
                return False
            self.nonce += 1
            self.hash = self.calculate_hash()
        return True

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "hash": self.hash
        }

class CriptoAPI:
    def __init__(self, node_port):
        self.p2p_port = node_port
        self.db_path = f"blockchain_node_{node_port}.db"
        self.db = BlockchainDB(self.db_path)
        self.mempool = []
        self.mempool_lock = threading.Lock()
        self.connected_peers = set()
        self.peers_lock = threading.Lock()
        self.chain_lock = threading.RLock()
        
        # Controle de Mineração Contínua
        self.is_mining = False
        self.mining_stop_event = threading.Event()
        self.miner_thread = None
        
        self._init_database()
        
        self.server_thread = threading.Thread(target=self._start_p2p_server, daemon=True)
        self.server_thread.start()
        
        threading.Thread(target=self._run_bootstrap_discovery, daemon=True).start()
        threading.Thread(target=self._peer_maintenance_loop, daemon=True).start()

    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocks (
                    id_index INTEGER PRIMARY KEY, timestamp REAL, previous_hash TEXT,
                    transactions TEXT, difficulty INTEGER, nonce INTEGER, hash TEXT
                )
            ''')
            cursor.execute('SELECT COUNT(*) FROM blocks')
            if cursor.fetchone()[0] == 0:
                genesis = BrunoBlock(0, "0", [{"sender": "SISTEMA", "receiver": GENESIS_ADDRESS, "amount": GENESIS_AMOUNT}], difficulty=4)
                genesis.mine_block()
                self.db.insert_block(genesis)

    def get_p2p_port(self):
        return self.p2p_port

    def _calculate_next_difficulty(self) -> int:
        """Ajuste dinâmico de dificuldade baseado no tempo gasto nos ultimos blocos"""
        chain = self.db.get_raw_chain()
        if len(chain) < DIFFICULTY_ADJUSTMENT_INTERVAL + 1:
            return chain[-1]["difficulty"]
        
        latest_block = chain[-1]
        if latest_block["index"] % DIFFICULTY_ADJUSTMENT_INTERVAL != 0:
            return latest_block["difficulty"]
            
        prev_adjustment_block = chain[-DIFFICULTY_ADJUSTMENT_INTERVAL]
        time_expected = TARGET_BLOCK_TIME * DIFFICULTY_ADJUSTMENT_INTERVAL
        time_taken = latest_block["timestamp"] - prev_adjustment_block["timestamp"]
        
        current_diff = latest_block["difficulty"]
        if time_taken < (time_expected / 2):
            return current_diff + 1
        elif time_taken > (time_expected * 2):
            return max(1, current_diff - 1)
        return current_diff

    def _receive_all(self, sock, buffer_size=4096, max_size=1_048_576):
        data = b""
        try:
            while True:
                chunk = sock.recv(buffer_size)
                if not chunk:
                    break
                data += chunk
                if len(data) > max_size:
                    raise ValueError(f"Mensagem excede tamanho maximo de {max_size} bytes")
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Erro ao receber dados: {e}")
        return data.decode('utf-8', errors='ignore')

    def _request_peer(self, ip, port, message, timeout=5.0):
        """Envia um pedido a um nó e devolve a resposta completa.

        O shutdown(SHUT_WR) é essencial: sem ele o servidor remoto continua
        aguardando EOF até o próprio timeout (5s) e só então responde, enquanto
        quem pediu já desistiu (3s). Era isso que impedia GET_HEIGHT/GET_CHAIN
        de concluir e fazia o nó "não enxergar" os demais.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((str(ip), int(port)))
            s.sendall(message.encode('utf-8'))
            s.shutdown(socket.SHUT_WR)
            return self._receive_all(s)
        finally:
            s.close()

    def _start_p2p_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.p2p_port))
        server_socket.listen(10)
        while True:
            try:
                client_conn, client_addr = server_socket.accept()
                client_conn.settimeout(5.0)
                data = self._receive_all(client_conn)

                if data == "GET_HEIGHT":
                    client_conn.sendall(str(len(self.db.get_raw_chain())).encode('utf-8'))
                elif data == "GET_CHAIN":
                    client_conn.sendall(json.dumps(self.db.get_raw_chain()).encode('utf-8'))
                elif data.startswith("ANNOUNCE_PEER:"):
                    # A porta de escuta de quem conecta não vem no endereço de
                    # origem (é efêmera), então ele a anuncia. Validamos
                    # reconectando antes de registrar, tornando o peer mútuo.
                    threading.Thread(
                        target=self._handle_peer_announcement,
                        args=(client_addr[0], data),
                        daemon=True,
                    ).start()
                elif data.startswith("BROADCAST_TX:"):
                    tx_data = json.loads(data.split(":", 1)[1])
                    if self._validate_transaction(tx_data, include_mempool=True)[0]:
                        with self.mempool_lock:
                            if tx_data not in self.mempool:
                                self.mempool.append(tx_data)
                elif data.startswith("SYNC_CHAIN:"):
                    incoming_chain = json.loads(data.split(":", 1)[1])
                    self._resolve_consensus(incoming_chain)
                client_conn.close()
            except Exception:
                pass

    def _local_ip_addresses(self):
        """Descobre os endereços IP desta máquina (loopback + LAN/WAN)."""
        ips = set()
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None):
                ips.add(info[4][0])
        except Exception:
            pass
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.settimeout(1.0)
            probe.connect(("8.8.8.8", 80))
            ips.add(probe.getsockname()[0])
            probe.close()
        except Exception:
            pass
        ips.add("127.0.0.1")
        return ips

    def _is_self(self, ip, port):
        """True apenas se (ip, porta) aponta para este próprio nó.

        A checagem antiga comparava só a porta e impedia conectar a outro
        computador que usasse a mesma porta (ex.: dois nós em 6001).
        """
        try:
            if int(port) != int(self.p2p_port):
                return False
        except (ValueError, TypeError):
            return False
        ip = str(ip).strip()
        if ip in ("127.0.0.1", "localhost", "0.0.0.0"):
            return True
        return ip in self._local_ip_addresses()

    def get_local_ips(self):
        """Endereços de escuta deste nó (o que informar ao outro computador)."""
        port = self.get_p2p_port()
        # O servidor escuta em 0.0.0.0 (somente IPv4), então não adianta
        # anunciar IPv6/link-local: o outro nó não conseguiria conectar.
        lan = sorted(
            ip for ip in self._local_ip_addresses()
            if "." in ip and not ip.startswith("127.") and not ip.startswith("169.254.")
        )
        return {
            "port": port,
            "loopback": f"127.0.0.1:{port}",
            "lan_addresses": [f"{ip}:{port}" for ip in lan],
        }

    def get_connected_peers(self):
        with self.peers_lock:
            peers = sorted(self.connected_peers, key=lambda p: (p[0], int(p[1])))
        return {
            "count": len(peers),
            "peers": [{"ip": ip, "port": int(port)} for ip, port in peers],
        }

    def _add_peer(self, ip, port):
        with self.peers_lock:
            self.connected_peers.add((str(ip).strip(), int(port)))

    def _remove_peer(self, ip, port):
        with self.peers_lock:
            self.connected_peers.discard((str(ip).strip(), int(port)))

    def _ping_peer(self, ip, port):
        try:
            self._request_peer(ip, port, "GET_HEIGHT", timeout=3.0)
            return True
        except Exception:
            return False

    def _handle_peer_announcement(self, peer_ip, data):
        """Registra um nó que se anunciou, após confirmar que ele é alcançável."""
        try:
            announced_port = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return
        if not announced_port or self._is_self(peer_ip, announced_port):
            return
        if self._ping_peer(peer_ip, announced_port):
            self._add_peer(peer_ip, announced_port)

    def _run_bootstrap_discovery(self):
        time.sleep(2)
        for ip, port in BOOTSTRAP_PEERS:
            if self._is_self(ip, port):
                continue
            try:
                self.connect_and_sync(ip, port)
            except Exception:
                pass

    def _peer_maintenance_loop(self):
        """Remove peers que pararam de responder e reconecta aos nós conhecidos."""
        while True:
            time.sleep(15)
            try:
                with self.peers_lock:
                    current = list(self.connected_peers)
                for ip, port in current:
                    if not self._ping_peer(ip, port):
                        self._remove_peer(ip, port)
                for ip, port in BOOTSTRAP_PEERS:
                    if self._is_self(ip, port):
                        continue
                    with self.peers_lock:
                        already = (str(ip).strip(), int(port)) in self.connected_peers
                    if not already:
                        self.connect_and_sync(ip, port)
            except Exception:
                pass

    def _broadcast_transaction_to_network(self, tx):
        with self.peers_lock:
            targets = list(self.connected_peers)
        for ip, port in targets:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((ip, int(port)))
                s.sendall(f"BROADCAST_TX:{json.dumps(tx)}".encode('utf-8'))
                s.close()
            except Exception:
                self._remove_peer(ip, port)

    def connect_and_sync(self, ip, port):
        try:
            port = int(port)
            remote_height = int(self._request_peer(ip, port, "GET_HEIGHT", timeout=5.0))

            # Registra o peer como alcançável MESMO quando a cadeia remota não é
            # maior. Antes ele só era registrado após baixar uma cadeia maior,
            # então blocos minerados e transações nunca eram propagados para
            # nós "empatados" — causa comum de não enxergar o outro computador.
            self._add_peer(ip, port)

            # Anuncia a própria porta para o remoto nos registrar de volta,
            # tornando a conexão mútua mesmo quando só este lado a iniciou.
            try:
                s_ann = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s_ann.settimeout(3.0)
                s_ann.connect((str(ip), port))
                s_ann.sendall(f"ANNOUNCE_PEER:{self.p2p_port}".encode('utf-8'))
                s_ann.close()
            except Exception:
                pass

            if remote_height <= len(self.db.get_raw_chain()):
                return {"status": "sucesso", "message": f"Conectado a {ip}:{port}. Sua blockchain já está atualizada."}

            response = self._request_peer(ip, port, "GET_CHAIN", timeout=15.0)
            return {"status": "sucesso", "message": self._resolve_consensus(json.loads(response))}
        except Exception as e:
            self._remove_peer(ip, port)
            return {"status": "erro", "message": str(e)}

    def _validate_address(self, address):
        if not isinstance(address, str) or not address.startswith("brn1") or len(address) != 44:
            raise ValueError(f"Tamanho ou formato de endereco invalido: {address}")
        try:
            int(address[4:], 16)
        except ValueError:
            raise ValueError("Endereco contem caracteres hexadecimais invalidos")
        return True

    @staticmethod
    def _canonical_amount(value) -> float:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError("Quantia inválida.")
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -8:
            raise ValueError("Quantia inválida; use até 8 casas decimais.")
        return float(amount)

    @staticmethod
    def _transaction_id(tx):
        signed = {key: tx[key] for key in ("sender", "receiver", "amount", "timestamp", "public_key", "signature")}
        return hashlib.sha256(json.dumps(signed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _available_balance(self, address, ignore_tx_id=None):
        balance = Decimal(str(self.get_balance(address).get("balance", 0)))
        with self.mempool_lock:
            for tx in self.mempool:
                if tx.get("sender") == address and tx.get("txid") != ignore_tx_id:
                    balance -= Decimal(str(tx["amount"]))
        return balance

    def _verify_tx_structure(self, tx) -> bool:
        """Verifica se a transação possui formato e assinatura validos"""
        if not isinstance(tx, dict):
            return False
        
        required_keys = ["sender", "receiver", "amount", "timestamp", "public_key", "signature"]
        if not all(k in tx for k in required_keys):
            return False
        try:
            self._validate_address(tx["sender"])
            self._validate_address(tx["receiver"])
            amount = self._canonical_amount(tx["amount"])
            timestamp = float(tx["timestamp"])
            if not timestamp or timestamp > time.time() + MAX_FUTURE_SECONDS:
                return False
            # Impede assinar com uma chave e declarar o endereço de outra carteira.
            if WalletManager.address_from_public_key(tx["public_key"]) != tx["sender"]:
                return False
            payload = {"sender": tx["sender"], "receiver": tx["receiver"], "amount": amount, "timestamp": timestamp}
            return WalletManager.verify_signature(tx["public_key"], payload, tx["signature"])
        except (ValueError, TypeError, KeyError):
            return False

    def _validate_transaction(self, tx, include_mempool=False):
        if not self._verify_tx_structure(tx):
            return False, "Transação inválida ou assinatura não confere."
        try:
            txid = self._transaction_id(tx)
            known_txids = {
                item.get("txid", self._transaction_id(item))
                for block in self.db.get_raw_chain() for item in block["transactions"]
                if item.get("sender") != "SISTEMA"
            }
            if txid in known_txids:
                return False, "Transação já confirmada."
            with self.mempool_lock:
                if any(item.get("txid", self._transaction_id(item)) == txid for item in self.mempool):
                    return False, "Transação já está na mempool."
            if include_mempool and self._available_balance(tx["sender"], txid) < Decimal(str(tx["amount"])):
                return False, "Saldo disponível insuficiente."
            return True, "OK"
        except (ValueError, KeyError, TypeError):
            return False, "Transação inválida."

    def _validate_block(self, block_data):
        required = {"index", "timestamp", "previous_hash", "transactions", "difficulty", "nonce", "hash"}
        if not isinstance(block_data, dict) or not required.issubset(block_data) or not isinstance(block_data["transactions"], list):
            return False, "Estrutura do bloco inválida"
        if not 1 <= int(block_data["difficulty"]) <= MAX_DIFFICULTY or len(block_data["transactions"]) > MAX_BLOCK_TRANSACTIONS:
            return False, "Limites do bloco inválidos"
        if float(block_data["timestamp"]) > time.time() + MAX_FUTURE_SECONDS:
            return False, "Timestamp futuro inválido"
        block = BrunoBlock(
            block_data["index"], block_data["previous_hash"], block_data["transactions"],
            block_data["difficulty"], block_data["nonce"], block_data["timestamp"], block_data["hash"]
        )
        if block.calculate_hash() != block_data["hash"]:
            return False, "Hash nao corresponde"
        
        target = "0" * block_data["difficulty"]
        if not block_data["hash"].startswith(target):
            return False, "Prova de Trabalho invalida"
            
        for position, tx in enumerate(block_data["transactions"]):
            if tx.get("sender") == "SISTEMA":
                expected_amount = GENESIS_AMOUNT if block.index == 0 else BLOCK_REWARD
                is_genesis = block.index == 0 and tx.get("receiver") == GENESIS_ADDRESS
                if position != 0 or tx.get("amount") != expected_amount or (not is_genesis and not self._is_valid_system_reward(tx)):
                    return False, "Recompensa de mineração inválida"
                if block.index == 0 and not is_genesis:
                    return False, "Bloco gênese inválido"
            elif not self._verify_tx_structure(tx):
                return False, f"Transacao invalida detectada no bloco: {tx}"
                
        return True, "OK"

    def _is_valid_system_reward(self, tx):
        try:
            self._validate_address(tx.get("receiver"))
            return set(tx) == {"sender", "receiver", "amount"}
        except ValueError:
            return False

    def _validate_chain_transactions(self, chain):
        """Reexecuta o ledger para bloquear gastos sem saldo e duplicidades."""
        balances = {}
        seen_txids = set()
        for block in chain:
            for tx in block["transactions"]:
                receiver = tx.get("receiver")
                amount = Decimal(str(tx.get("amount", 0)))
                if tx.get("sender") == "SISTEMA":
                    balances[receiver] = balances.get(receiver, Decimal("0")) + amount
                    continue
                if not self._verify_tx_structure(tx):
                    return False, "Transação inválida no ledger remoto."
                txid = self._transaction_id(tx)
                if txid in seen_txids:
                    return False, "Transação duplicada no ledger remoto."
                seen_txids.add(txid)
                sender = tx["sender"]
                if balances.get(sender, Decimal("0")) < amount:
                    return False, "Gasto sem saldo no ledger remoto."
                balances[sender] -= amount
                balances[receiver] = balances.get(receiver, Decimal("0")) + amount
        return True, "OK"

    def _resolve_consensus(self, remote_chain) -> str:
        if len(remote_chain) <= len(self.db.get_raw_chain()):
            return "Cadeia local ja e dominante."
            
        if not isinstance(remote_chain, list) or not remote_chain:
            return "Cadeia remota inválida."
        if remote_chain[0].get("index") != 0 or remote_chain[0].get("previous_hash") != "0":
            return "Gênese remota inválida."
        for i in range(1, len(remote_chain)):
            if remote_chain[i]["index"] != remote_chain[i - 1]["index"] + 1 or remote_chain[i]["timestamp"] < remote_chain[i - 1]["timestamp"]:
                return "Ordem de blocos inválida na cadeia remota."
            if remote_chain[i]["previous_hash"] != remote_chain[i-1]["hash"]:
                return "Hashes corrompidos na cadeia remota."
                
        for block_data in remote_chain:
            is_valid, message = self._validate_block(block_data)
            if not is_valid:
                return f"Bloco #{block_data['index']} rejeitado: {message}"
        is_valid, message = self._validate_chain_transactions(remote_chain)
        if not is_valid:
            return f"Cadeia remota rejeitada: {message}"
                
        with self.chain_lock:
            self.db.replace_chain(remote_chain)
        return f"Sincronizado com sucesso para {len(remote_chain)} blocos."

    def save_encrypted_wallet(self, filename, password, address, spend_secret_key, public_key=""):
        return WalletManager.save_encrypted_wallet(filename, password, address, spend_secret_key, public_key)

    def load_encrypted_wallet(self, filename, password):
        return WalletManager.load_encrypted_wallet(filename, password)

    def get_full_chain(self):
        with self.mempool_lock:
            mempool_size = len(self.mempool)
        chain = self.db.get_raw_chain()
        return {
            "chain": chain, 
            "length": len(chain), 
            "mempool_size": mempool_size,
            "is_mining": self.is_mining,
            "current_difficulty": chain[-1]["difficulty"] if chain else 4
        }

    def generate_wallet(self):
        return WalletManager.generate_keypair()

    def get_balance(self, address):
        try:
            self._validate_address(address)
            balance = Decimal("0")
            for b in self.db.get_raw_chain():
                for tx in b["transactions"]:
                    if tx.get("sender") == address:
                        balance -= Decimal(str(tx.get("amount", 0)))
                    if tx.get("receiver") == address:
                        balance += Decimal(str(tx.get("amount", 0)))
            return {"address": address, "balance": float(balance)}
        except ValueError as e:
            return {"status": "erro", "message": str(e)}

    def get_transaction_history(self, address):
        """Extrato de envios e recebimentos de um endereço (chain confirmada + mempool)."""
        try:
            self._validate_address(address)
        except ValueError as e:
            return {"status": "erro", "message": str(e)}

        def _amount(tx):
            try:
                return float(Decimal(str(tx.get("amount", 0))))
            except (InvalidOperation, ValueError):
                return 0.0

        entries = []
        chain = self.db.get_raw_chain()
        chain_len = len(chain)
        for block in chain:
            block_index = block["index"]
            block_ts = float(block.get("timestamp", 0) or 0)
            confirmations = max(0, chain_len - block_index)
            for tx in block["transactions"]:
                sender = tx.get("sender")
                receiver = tx.get("receiver")
                ts = float(tx.get("timestamp") or block_ts)
                if receiver == address:
                    if sender == "SISTEMA":
                        tx_type = "genese" if block_index == 0 else "mineracao"
                        counterparty = "SISTEMA (Rede)"
                    else:
                        tx_type = "recebido"
                        counterparty = sender
                    entries.append({
                        "direction": "entrada", "type": tx_type, "amount": _amount(tx),
                        "counterparty": counterparty, "timestamp": ts, "block_index": block_index,
                        "confirmations": confirmations, "status": "confirmada", "txid": tx.get("txid", ""),
                    })
                elif sender == address:
                    entries.append({
                        "direction": "saida", "type": "enviado", "amount": _amount(tx),
                        "counterparty": receiver, "timestamp": ts, "block_index": block_index,
                        "confirmations": confirmations, "status": "confirmada", "txid": tx.get("txid", ""),
                    })

        with self.mempool_lock:
            pending = list(self.mempool)
        for tx in pending:
            sender = tx.get("sender")
            receiver = tx.get("receiver")
            ts = float(tx.get("timestamp") or 0)
            if receiver == address:
                entries.append({
                    "direction": "entrada", "type": "recebido", "amount": _amount(tx),
                    "counterparty": sender, "timestamp": ts, "block_index": None,
                    "confirmations": 0, "status": "pendente", "txid": tx.get("txid", ""),
                })
            elif sender == address:
                entries.append({
                    "direction": "saida", "type": "enviado", "amount": _amount(tx),
                    "counterparty": receiver, "timestamp": ts, "block_index": None,
                    "confirmations": 0, "status": "pendente", "txid": tx.get("txid", ""),
                })

        entries.sort(
            key=lambda e: (e["timestamp"], e["block_index"] if e["block_index"] is not None else float("inf")),
            reverse=True,
        )
        return {"status": "sucesso", "address": address, "history": entries}

    def send_funds(self, sender, receiver, amount, spend_secret_key, public_key):
        try:
            self._validate_address(sender)
            self._validate_address(receiver)
            sender, receiver = str(sender).strip(), str(receiver).strip()
            amount = self._canonical_amount(amount)
                
            tx_payload = {
                "sender": str(sender).strip(),
                "receiver": str(receiver).strip(),
                "amount": amount,
                "timestamp": time.time()
            }
            
            signature = WalletManager.sign_transaction(spend_secret_key, tx_payload)
            full_tx = {
                **tx_payload,
                "public_key": public_key,
                "signature": signature
            }
            full_tx["txid"] = self._transaction_id(full_tx)
            valid, message = self._validate_transaction(full_tx, include_mempool=True)
            if not valid:
                return {"status": "erro", "message": message}
            
            with self.mempool_lock:
                self.mempool.append(full_tx)
                
            threading.Thread(target=self._broadcast_transaction_to_network, args=(full_tx,), daemon=True).start()
            return {"status": "sucesso", "message": "Transacao assinada e enviada a mempool!"}
        except Exception as e:
            return {"status": "erro", "message": str(e)}

    # Controladores de Mineração Contínua
    def toggle_continuous_mining(self, miner_address):
        if self.is_mining:
            self.is_mining = False
            self.mining_stop_event.set()
            return {"status": "sucesso", "message": "Mineracao continua pausada.", "is_mining": False}
        else:
            try:
                self._validate_address(miner_address)
                self.is_mining = True
                self.mining_stop_event.clear()
                self.miner_thread = threading.Thread(target=self._continuous_mining_loop, args=(miner_address,), daemon=True)
                self.miner_thread.start()
                return {"status": "sucesso", "message": "Mineracao continua iniciada!", "is_mining": True}
            except Exception as e:
                return {"status": "erro", "message": str(e)}

    def _continuous_mining_loop(self, miner_address):
        print(f"⛏️ Loop de mineracao continua ativo para: {miner_address}")
        while self.is_mining and not self.mining_stop_event.is_set():
            try:
                local_chain = self.db.get_raw_chain()
                last_block = local_chain[-1]
                next_difficulty = self._calculate_next_difficulty()
                
                with self.mempool_lock:
                    pending = list(self.mempool)
                    bloco_txs = [
                        {"sender": "SISTEMA", "receiver": str(miner_address).strip(), "amount": BLOCK_REWARD}
                    ] + pending
                    
                new_block = BrunoBlock(
                    last_block["index"] + 1,
                    last_block["hash"],
                    bloco_txs,
                    difficulty=next_difficulty
                )
                
                success = new_block.mine_block(stop_event=self.mining_stop_event)
                if success and self.is_mining:
                    with self.chain_lock:
                        # Não anexar sobre uma ponta que foi alterada durante a PoW.
                        current_tip = self.db.get_raw_chain()[-1]
                        if current_tip["hash"] != new_block.previous_hash:
                            continue
                        self.db.insert_block(new_block)
                    with self.mempool_lock:
                        self.mempool = [tx for tx in self.mempool if tx not in pending]
                    
                    raw_chain_json = json.dumps(self.db.get_raw_chain())
                    for ip, port in list(self.connected_peers):
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(3.0)
                            s.connect((ip, int(port)))
                            s.sendall(f"SYNC_CHAIN:{raw_chain_json}".encode('utf-8'))
                            s.close()
                        except Exception:
                            pass
                    print(f"✅ Bloco #{new_block.index} minerado (Diff: {next_difficulty}). Hash: {new_block.hash[:16]}...")
            except Exception as e:
                print(f"⚠️ Erro no loop de mineracao: {e}")
                time.sleep(2)
        print("🛑 Loop de mineracao continua desligado.")

if __name__ == '__main__':
    p2p_port = 6001
    if len(sys.argv) > 1:
        try:
            p2p_port = int(sys.argv[1])
        except ValueError:
            pass
    # UPnP não é ativado automaticamente: expor a carteira à internet sem a
    # confirmação do dono é arriscado. A sincronização manual continua disponível.
    api_local = CriptoAPI(p2p_port)
    webview.create_window(title=f"Carteira Nativa {COIN_NAME} (Porta: {p2p_port})", url="index.html", js_api=api_local, width=740, height=800, resizable=True)
    webview.start()
