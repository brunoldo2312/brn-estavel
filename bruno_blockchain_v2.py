"""
bruno_blockchain_v2.py
Motor principal da Moeda Bruno v2.
Implementa: PoW (SHA-256), dificuldade ajustável, halving,
suprimento máximo, modelo UTXO, Merkle Root e taxas de transação.
"""

import hashlib
import json
import time
import socket
import threading
from decimal import Decimal, getcontext
from typing import List, Optional, Set

from cripto_db_v2 import BlockchainDB
from cripto_wallet_v2 import Wallet
from cripto_p2p_network import P2PManager

getcontext().prec = 18

# ============================================================
# PARÂMETROS DA REDE
# ============================================================
COIN_NAME = "Moeda Bruno"
COIN_SYMBOL = "BRN"
MAX_SUPPLY = Decimal("21000000")
INITIAL_REWARD = Decimal("50")
HALVING_INTERVAL = 210000
TARGET_BLOCK_TIME = 10.0
DIFFICULTY_ADJUSTMENT_INTERVAL = 5
INITIAL_DIFFICULTY = 4
MAX_DIFFICULTY = 8
MIN_TX_FEE = Decimal("0.0001")

GENESIS_TIMESTAMP = 1700000000.0
GENESIS_NONCE = 171419
GENESIS_ADDRESS = "brn1111cd943fa71e1f91dcd62f52fc6138bc845ab"
GENESIS_HASH = "0000d904d5f2954d5c9aa43eafed2f885ad17c5047605ed6e385458b590fcaff"


# ============================================================
# MERKLE ROOT
# ============================================================
def compute_merkle_root(txids: List[str]) -> str:
    if not txids:
        return hashlib.sha256(b"").hexdigest()
    layer = [bytes.fromhex(t) for t in txids]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest()
                 for i in range(0, len(layer), 2)]
    return layer[0].hex()


# ============================================================
# CLASSES DE DADOS
# ============================================================
class TxInput:
    def __init__(self, txid, output_index, signature=""):
        self.txid = txid
        self.output_index = output_index
        self.signature = signature

    def to_dict(self):
        return {"txid": self.txid, "output_index": self.output_index,
                "signature": self.signature}

    @staticmethod
    def from_dict(d):
        return TxInput(d["txid"], d["output_index"], d.get("signature", ""))


class TxOutput:
    def __init__(self, address, amount):
        self.address = address
        self.amount = str(amount)

    def to_dict(self):
        return {"address": self.address, "amount": self.amount}

    @staticmethod
    def from_dict(d):
        return TxOutput(d["address"], d["amount"])


class Transaction:
    def __init__(self, inputs, outputs, timestamp=None, fee="0", coinbase=False):
        self.inputs = inputs
        self.outputs = outputs
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.fee = str(fee)
        self.coinbase = coinbase
        self.txid = self._compute_txid()

    def _compute_txid(self):
        payload = {
            "inputs": [(i.txid, i.output_index) for i in self.inputs],
            "outputs": [(o.address, o.amount) for o in self.outputs],
            "timestamp": self.timestamp,
            "coinbase": self.coinbase,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def to_dict(self):
        return {
            "txid": self.txid,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "timestamp": self.timestamp,
            "fee": self.fee,
            "coinbase": self.coinbase,
        }

    @staticmethod
    def from_dict(d):
        return Transaction(
            inputs=[TxInput.from_dict(i) for i in d["inputs"]],
            outputs=[TxOutput.from_dict(o) for o in d["outputs"]],
            timestamp=d["timestamp"], fee=d["fee"], coinbase=bool(d["coinbase"])
        )


class Block:
    def __init__(self, height, previous_hash, merkle_root, timestamp,
                 difficulty, nonce, transactions, block_hash=""):
        self.height = height
        self.previous_hash = previous_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.nonce = nonce
        self.transactions = transactions
        self.hash = block_hash or self._calculate_hash()

    def _calculate_hash(self):
        header = (f"{self.height}{self.previous_hash}{self.merkle_root}"
                  f"{self.timestamp}{self.difficulty}{self.nonce}")
        return hashlib.sha256(header.encode()).hexdigest()

    def mine(self, stop_event=None):
        target = "0" * self.difficulty
        while not self.hash.startswith(target):
            if stop_event and stop_event.is_set():
                return False
            self.nonce += 1
            self.hash = self._calculate_hash()
        return True

    def to_dict(self):
        return {
            "height": self.height,
            "hash": self.hash,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "transactions": [t.to_dict() for t in self.transactions],
        }


# ============================================================
# MOTOR PRINCIPAL
# ============================================================
class CriptoAPI:
    def __init__(self, node_port):
        self.p2p_port = node_port
        self.db = BlockchainDB(f"brn_v2_chain_{node_port}.db")
        self.mempool: List[Transaction] = []
        self.mempool_lock = threading.Lock()
        self.peers: Set[str] = set()
        self.is_mining = False
        self.mining_stop = threading.Event()
        self.miner_thread = None

        self._init_genesis()

        # Inicia P2P completo
        self.p2p = P2PManager(self, node_port, enable_upnp=True)
        self.p2p.start()

    # ---------- GÊNESE ----------
    def _init_genesis(self):
        if self.db.chain_height() < 0:
            coinbase = Transaction(
                inputs=[],
                outputs=[TxOutput(GENESIS_ADDRESS, "0")],
                timestamp=GENESIS_TIMESTAMP, fee="0", coinbase=True
            )
            genesis = Block(
                height=0, previous_hash="0" * 64,
                merkle_root=compute_merkle_root([coinbase.txid]),
                timestamp=GENESIS_TIMESTAMP,
                difficulty=INITIAL_DIFFICULTY,
                nonce=GENESIS_NONCE,
                transactions=[coinbase]
            )
            genesis.hash = GENESIS_HASH
            self.db.save_block(genesis.to_dict())
            print(f"[GENESIS v2] Bloco 0 salvo: {genesis.hash}")

    # ---------- POLÍTICA MONETÁRIA ----------
    def current_reward(self) -> Decimal:
        height = self.db.chain_height() + 1
        halvings = height // HALVING_INTERVAL
        reward = INITIAL_REWARD / (Decimal(2) ** halvings)
        total = self.db.total_mined()
        if total + reward > MAX_SUPPLY:
            reward = MAX_SUPPLY - total
        return max(reward, Decimal("0"))

    def current_difficulty(self) -> int:
        h = self.db.chain_height()
        if h < DIFFICULTY_ADJUSTMENT_INTERVAL:
            return INITIAL_DIFFICULTY
        if h % DIFFICULTY_ADJUSTMENT_INTERVAL != 0:
            last = self.db.get_last_block()
            return last["difficulty"] if last else INITIAL_DIFFICULTY
        c = self.db.conn.cursor()
        rows = c.execute("SELECT timestamp FROM blocks WHERE height IN (?,?) ORDER BY height",
                         (h - DIFFICULTY_ADJUSTMENT_INTERVAL, h)).fetchall()
        if len(rows) < 2:
            return INITIAL_DIFFICULTY
        elapsed = rows[1]["timestamp"] - rows[0]["timestamp"]
        expected = TARGET_BLOCK_TIME * DIFFICULTY_ADJUSTMENT_INTERVAL
        last_diff = self.db.get_last_block()["difficulty"]
        if elapsed < expected / 2:
            return min(last_diff + 1, MAX_DIFFICULTY)
        elif elapsed > expected * 2:
            return max(last_diff - 1, 1)
        return last_diff

    # ---------- MINERAÇÃO ----------
    def mine_block(self, miner_address):
        last = self.db.get_last_block()
        height = (last["height"] + 1) if last else 0
        reward = self.current_reward()
        difficulty = self.current_difficulty()

        if reward <= 0:
            print("[MINERAÇÃO] Suprimento máximo atingido. Parando.")
            self.stop_mining()
            return None

        coinbase = Transaction(
            inputs=[],
            outputs=[TxOutput(miner_address, str(reward))],
            timestamp=time.time(), fee="0", coinbase=True
        )

        with self.mempool_lock:
            selected = self.mempool[:100]
            self.mempool = self.mempool[100:]

        txs = [coinbase] + selected
        block = Block(
            height=height,
            previous_hash=last["hash"] if last else "0" * 64,
            merkle_root=compute_merkle_root([t.txid for t in txs]),
            timestamp=time.time(),
            difficulty=difficulty,
            nonce=0,
            transactions=txs
        )
        print(f"[MINERANDO] Bloco {height} | Diff {difficulty} | Recompensa {reward} BRN")
        start = time.time()
        if not block.mine(self.mining_stop):
            return None
        elapsed = time.time() - start
        print(f"[MINERADO] {block.hash[:24]}... em {elapsed:.2f}s | {len(txs)} tx")
        self.db.save_block(block.to_dict())

        # Propaga o bloco para os peers
        self.p2p.broadcast_block(block.to_dict())
        return block

    def start_mining(self, miner_address):
        if self.is_mining:
            return False, "Mineração já ativa"
        self.is_mining = True
        self.mining_stop.clear()

        def loop():
            while not self.mining_stop.is_set():
                try:
                    self.mine_block(miner_address)
                except Exception as e:
                    print(f"[MINERAÇÃO] Erro: {e}")
                    time.sleep(2)

        self.miner_thread = threading.Thread(target=loop, daemon=True)
        self.miner_thread.start()
        return True, "Mineração iniciada"

    def stop_mining(self):
        self.is_mining = False
        self.mining_stop.set()
        return True, "Mineração parada"

    # ---------- TRANSAÇÕES ----------
    def create_transaction(self, wallet: Wallet, to_address, amount, fee=None):
        fee = fee or str(MIN_TX_FEE)
        amount_dec = Decimal(str(amount))
        fee_dec = Decimal(str(fee))

        utxos = self.db.get_utxos(wallet.address)
        if not utxos:
            return None, "Sem UTXOs disponíveis"

        target = amount_dec + fee_dec
        selected, total = [], Decimal("0")
        for u in utxos:
            selected.append(u)
            total += Decimal(u["amount"])
            if total >= target:
                break
        if total < target:
            return None, f"Saldo insuficiente: {total} < {target}"

        inputs = [TxInput(txid=u["txid"], output_index=u["output_index"]) for u in selected]
        outputs = [TxOutput(to_address, str(amount_dec))]

        change = total - target
        if change > 0:
            outputs.append(TxOutput(wallet.address, str(change)))

        tx = Transaction(inputs=inputs, outputs=outputs,
                         timestamp=time.time(), fee=fee, coinbase=False)
        sig = wallet.sign(tx.txid)
        for i in inputs:
            i.signature = sig
        return tx, "OK"

    def submit_transaction(self, tx: Transaction):
        if Decimal(tx.fee) < MIN_TX_FEE:
            return False, f"Taxa abaixo do mínimo ({MIN_TX_FEE})"

        input_total = Decimal("0")
        for inp in tx.inputs:
            c = self.db.conn.cursor()
            row = c.execute("SELECT * FROM utxos WHERE txid=? AND output_index=? AND spent=0",
                            (inp.txid, inp.output_index)).fetchone()
            if not row:
                return False, f"UTXO inexistente ou já gasto: {inp.txid[:16]}"
            input_total += Decimal(row["amount"])

        output_total = sum((Decimal(o.amount) for o in tx.outputs), Decimal("0"))
        if input_total < output_total + Decimal(tx.fee):
            return False, "Saldo insuficiente"

        with self.mempool_lock:
            for pending in self.mempool:
                for pinp in pending.inputs:
                    for inp in tx.inputs:
                        if pinp.txid == inp.txid and pinp.output_index == inp.output_index:
                            return False, "Gasto duplo detectado na mempool"
            self.mempool.append(tx)

        # Propaga a transação para os peers
        self.p2p.broadcast_tx(tx.to_dict())
        return True, f"Transação {tx.txid[:16]}... adicionada à mempool"

    # ---------- MÉTODOS PARA main.py / explorer.py ----------
    def get_full_chain(self):
        return self.db.get_full_chain()

    def get_balance(self, address):
        return str(self.db.balance(address))

    def get_transaction_history(self, address):
        return self.db.get_transactions_by_address(address)

    def get_mempool(self):
        return [t.to_dict() for t in self.mempool]

    def get_connected_peers(self):
        return list(self.p2p.discovery.get_peers().keys())

    def get_local_ips(self):
        try:
            hostname = socket.gethostname()
            return list(set(socket.gethostbyname_ex(hostname)[2]))
        except Exception:
            return []

    def get_status(self):
        p2p_status = self.p2p.get_status()
        return {
            "coin": COIN_NAME,
            "symbol": COIN_SYMBOL,
            "height": self.db.chain_height(),
            "difficulty": self.current_difficulty(),
            "reward": str(self.current_reward()),
            "total_mined": str(self.db.total_mined()),
            "max_supply": str(MAX_SUPPLY),
            "mempool_size": len(self.mempool),
            "peers": p2p_status["peer_count"],
            "external_ip": p2p_status["external_ip"],
            "is_mining": self.is_mining,
        }

    # ---------- MÉTODOS PARA A GUI ----------
    def get_wallet_info(self):
        """Retorna informações da carteira atual (usado pela GUI)."""
        # A carteira é gerenciada pelo main.py; aqui retornamos um placeholder.
        # O main.py injeta o endereço da carteira no objeto api.
        return {"address": getattr(self, "wallet_address", "brn1...")}

    def send_from_gui(self, to_address, amount, fee="0.0001"):
        """Método chamado pela GUI para enviar transação."""
        if not hasattr(self, "wallet"):
            return "Erro: carteira não configurada"
        tx, msg = self.create_transaction(self.wallet, to_address, amount, fee)
        if not tx:
            return msg
        ok, m = self.submit_transaction(tx)
        return m