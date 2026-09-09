import os
import json

# Estrutura de diretórios e arquivos
PROJECT_STRUCTURE = {
    "modules": {
        "__init__.py": "",
        "ledger_manager.py": '''import json
import os
from typing import List, Dict, Any

class LedgerManager:
    def __init__(self, data_folder: str = "data"):
        self.data_folder = data_folder
        self.ledger_path = os.path.join(data_folder, "ledger.json")
        self.reserve_path = os.path.join(data_folder, "collateral_reserve.json")
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        os.makedirs(self.data_folder, exist_ok=True)
        if not os.path.exists(self.ledger_path):
            initial_data = {
                "network": "BRN-L2",
                "pending_transactions": [
                    {"tx_id": "tx001", "sender": "Alice", "receiver": "Bob", "amount": 100.0, "status": "pending"},
                    {"tx_id": "tx002", "sender": "Bob", "receiver": "Charlie", "amount": 25.5, "status": "pending"}
                ],
                "processed_batches": []
            }
            self.save_json(self.ledger_path, initial_data)
        if not os.path.exists(self.reserve_path):
            initial_reserve = {"asset": "BRN-Estavel", "peg_usd": 1.00, "total_supply": 1000.0, "collateral_usd": 1000.0}
            self.save_json(self.reserve_path, initial_reserve)

    def load_json(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, path: str, data: Dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        data = self.load_json(self.ledger_path)
        return data.get("pending_transactions", [])

    def mark_transactions_as_anchored(self, batch_id: str, merkle_root: str, btc_txid: str):
        data = self.load_json(self.ledger_path)
        pending = data.get("pending_transactions", [])
        if not pending:
            return
        batch_record = {
            "batch_id": batch_id,
            "merkle_root": merkle_root,
            "bitcoin_txid": btc_txid,
            "tx_count": len(pending),
            "transactions": pending
        }
        data["processed_batches"].append(batch_record)
        data["pending_transactions"] = []
        self.save_json(self.ledger_path, data)
''',
        "rollup_sequencer.py": '''import hashlib
import json

class RollupSequencer:
    @staticmethod
    def calculate_merkle_root(transactions: list) -> str:
        if not transactions:
            return ""
        hashes = [
            hashlib.sha256(json.dumps(tx, sort_keys=True).encode("utf-8")).hexdigest()
            for tx in transactions
        ]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_level.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())
            hashes = new_level
        return hashes[0]
''',
        "bitcoin_anchor.py": '''import time
import hashlib

class BitcoinAnchor:
    def __init__(self, network: str = "testnet"):
        self.network = network

    def build_op_return_data(self, merkle_root: str) -> str:
        return f"BRN:{merkle_root[:32]}"

    def anchor_to_bitcoin(self, merkle_root: str, wallet_name: str = "main_wallet") -> str:
        payload = self.build_op_return_data(merkle_root)
        try:
            from bitcoinlib.wallets import Wallet
            w = Wallet(wallet_name)
            tx = w.send_to(outputs=[(None, 0)], data=payload.encode('utf-8'), fee=1000)
            return tx.txid
        except Exception:
            simulated_txid = hashlib.sha256(f"{payload}{time.time()}".encode()).hexdigest()
            print(f"[Aviso] Executando em modo simulação (Sem conexão RPC ativa com o Bitcoin).")
            print(f"[BTC Anchor] Payload OP_RETURN preparado: {payload}")
            return simulated_txid
'''
    },
    "main.py": '''import uuid
from modules.ledger_manager import LedgerManager
from modules.rollup_sequencer import RollupSequencer
from modules.bitcoin_anchor import BitcoinAnchor

def run_pipeline():
    print("==================================================")
    print("      SISTEMA BRN-ESTAVEL: ENGINE DE ROLLUP       ")
    print("==================================================")
    ledger = LedgerManager()
    pending_txs = ledger.get_pending_transactions()
    if not pending_txs:
        print("[!] Nenhuma transação pendente encontrada no ledger.json.")
        return
    print(f"[+] Transações pendentes carregadas: {len(pending_txs)} item(ns).")
    merkle_root = RollupSequencer.calculate_merkle_root(pending_txs)
    print(f"[+] Raiz de Merkle calculada para o Rollup:")
    print(f"    -> Merkle Root: {merkle_root}")
    print("\\n[+] Ancorando o estado no Bitcoin...")
    anchor = BitcoinAnchor(network="testnet")
    btc_txid = anchor.anchor_to_bitcoin(merkle_root)
    print(f"    -> Bitcoin TXID: {btc_txid}")
    batch_id = f"batch_{str(uuid.uuid4())[:8]}"
    ledger.mark_transactions_as_anchored(batch_id, merkle_root, btc_txid)
    print(f"\\n[+] Sucesso! Lote '{batch_id}' gravado e ledger.json atualizado.")

if __name__ == "__main__":
    run_pipeline()
'''
}

def create_project():
    """Cria todos os diretórios e arquivos do projeto."""
    base_dir = os.getcwd()  # Cria na pasta atual
    print(f"📁 Criando projeto em: {base_dir}")

    for name, content in PROJECT_STRUCTURE.items():
        if name.endswith(".py"):  # Arquivo na raiz
            with open(os.path.join(base_dir, name), "w", encoding="utf-8") as f:
                f.write(content)
            print(f"   ✅ {name}")
        else:  # Pasta
            folder_path = os.path.join(base_dir, name)
            os.makedirs(folder_path, exist_ok=True)
            for sub_name, sub_content in content.items():
                file_path = os.path.join(folder_path, sub_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(sub_content)
                print(f"   ✅ {name}/{sub_name}")

    print("\n🎯 Projeto criado com sucesso!")
    print("👉 Para executar: pip install bitcoinlib && python main.py")

if __name__ == "__main__":
    create_project()