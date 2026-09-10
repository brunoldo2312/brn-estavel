"""Nó BRN headless — blockchain + P2P em um único event loop."""
import asyncio
import sys
from blockchain import Blockchain
from p2p import PeerManager

async def run(port: int, db_path: str, miner_address: str | None = None, mine: bool = False):
    bc = Blockchain(db_path=db_path, genesis_address=miner_address)
    pm = PeerManager(bc, port)
    await pm.start()
    if mine and miner_address:
        asyncio.create_task(_mine_loop(bc, miner_address, pm))
    print(f"[BRN] nó iniciado. Altura={bc.db.height()} tip={bc.db.tip_hash()[:16]}")
    while True:
        await asyncio.sleep(3600)

async def _mine_loop(bc: Blockchain, address: str, pm: PeerManager):
    while True:
        try:
            block = await asyncio.to_thread(bc.mine_block, address)
            if block:
                print(f"[MINE] bloco {block['height']} {block['hash'][:16]} "
                      f"txs={len(block['transactions'])} diff={block['difficulty']}")
                await pm.broadcast({"type": "inv_block",
                                    "height": block["height"],
                                    "hash": block["hash"]})
        except Exception as e:
            print(f"[MINE] erro: {e}")
        await asyncio.sleep(2)

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6001
    db_path = sys.argv[2] if len(sys.argv) > 2 else f"blockchain_node_{port}.db"
    miner_address = sys.argv[3] if len(sys.argv) > 3 else None
    mine = "--mine" in sys.argv
    try:
        asyncio.run(run(port, db_path, miner_address, mine))
    except KeyboardInterrupt:
        print("\n[BRN] encerrado")

if __name__ == "__main__":
    main()