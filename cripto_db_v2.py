"""
cripto_db_v2.py
Camada de persistência SQLite3 com suporte a UTXO e Merkle Root.
"""
import sqlite3
import json
import threading
from decimal import Decimal


class BlockchainDB:
    def __init__(self, path="brn_v2_chain.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS blocks (
                height INTEGER PRIMARY KEY,
                hash TEXT UNIQUE,
                previous_hash TEXT,
                merkle_root TEXT,
                timestamp REAL,
                difficulty INTEGER,
                nonce INTEGER
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS transactions (
                txid TEXT PRIMARY KEY,
                block_height INTEGER,
                timestamp REAL,
                fee TEXT,
                coinbase INTEGER,
                raw TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS utxos (
                txid TEXT,
                output_index INTEGER,
                address TEXT,
                amount TEXT,
                block_height INTEGER,
                spent INTEGER DEFAULT 0,
                PRIMARY KEY (txid, output_index)
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_utxo_addr ON utxos(address, spent)")
            self.conn.commit()

    def save_block(self, block_dict):
        """block_dict: {height, hash, previous_hash, merkle_root,
                        timestamp, difficulty, nonce, transactions: [tx_dict]}"""
        with self.lock:
            c = self.conn.cursor()
            c.execute("INSERT OR REPLACE INTO blocks VALUES (?,?,?,?,?,?,?)",
                      (block_dict["height"], block_dict["hash"],
                       block_dict["previous_hash"], block_dict["merkle_root"],
                       block_dict["timestamp"], block_dict["difficulty"],
                       block_dict["nonce"]))
            for tx in block_dict["transactions"]:
                c.execute("INSERT OR REPLACE INTO transactions VALUES (?,?,?,?,?,?)",
                          (tx["txid"], block_dict["height"], tx["timestamp"],
                           tx["fee"], 1 if tx["coinbase"] else 0,
                           json.dumps(tx)))
                for inp in tx["inputs"]:
                    c.execute("UPDATE utxos SET spent=1 WHERE txid=? AND output_index=?",
                              (inp["txid"], inp["output_index"]))
                for idx, out in enumerate(tx["outputs"]):
                    c.execute("INSERT OR REPLACE INTO utxos VALUES (?,?,?,?,?,0)",
                              (tx["txid"], idx, out["address"],
                               out["amount"], block_dict["height"]))
            self.conn.commit()

    def get_utxos(self, address):
        c = self.conn.cursor()
        return [dict(r) for r in c.execute(
            "SELECT * FROM utxos WHERE address=? AND spent=0", (address,)).fetchall()]

    def balance(self, address):
        utxos = self.get_utxos(address)
        return sum((Decimal(u["amount"]) for u in utxos), Decimal("0"))

    def get_last_block(self):
        c = self.conn.cursor()
        row = c.execute("SELECT * FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
        if not row:
            return None
        txs = []
        for tr in c.execute("SELECT raw FROM transactions WHERE block_height=? ORDER BY rowid",
                            (row["height"],)).fetchall():
            txs.append(json.loads(tr["raw"]))
        return {"height": row["height"], "hash": row["hash"],
                "previous_hash": row["previous_hash"], "merkle_root": row["merkle_root"],
                "timestamp": row["timestamp"], "difficulty": row["difficulty"],
                "nonce": row["nonce"], "transactions": txs}

    def get_block(self, height):
        c = self.conn.cursor()
        row = c.execute("SELECT * FROM blocks WHERE height=?", (height,)).fetchone()
        if not row:
            return None
        txs = []
        for tr in c.execute("SELECT raw FROM transactions WHERE block_height=? ORDER BY rowid",
                            (height,)).fetchall():
            txs.append(json.loads(tr["raw"]))
        return {"height": row["height"], "hash": row["hash"],
                "previous_hash": row["previous_hash"], "merkle_root": row["merkle_root"],
                "timestamp": row["timestamp"], "difficulty": row["difficulty"],
                "nonce": row["nonce"], "transactions": txs}

    def get_full_chain(self):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM blocks ORDER BY height").fetchall()
        return [dict(r) for r in rows]

    def get_transactions_by_address(self, address):
        c = self.conn.cursor()
        rows = c.execute("""SELECT raw FROM transactions
                            WHERE raw LIKE ? ORDER BY timestamp DESC""",
                         (f'%"{address}"%',)).fetchall()
        return [json.loads(r["raw"]) for r in rows]

    def chain_height(self):
        c = self.conn.cursor()
        row = c.execute("SELECT MAX(height) as h FROM blocks").fetchone()
        return row["h"] if row and row["h"] is not None else -1

    def total_mined(self):
        c = self.conn.cursor()
        row = c.execute("SELECT SUM(CAST(amount AS REAL)) as s FROM utxos").fetchone()
        return Decimal(str(row["s"])) if row and row["s"] else Decimal("0")

    def close(self):
        self.conn.close()