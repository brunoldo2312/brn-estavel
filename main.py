"""Launcher BRN — headless por padrão, GUI opcional, explorador embutido."""
import argparse
import subprocess
import sys
import time
import webbrowser

def main():
    p = argparse.ArgumentParser(description="BRN v2 — nó headless")
    p.add_argument("--port", type=int, default=6001)
    p.add_argument("--db", default=None, help="caminho do banco")
    p.add_argument("--miner", default=None, help="endereço bech32 brn1...")
    p.add_argument("--mine", action="store_true")
    p.add_argument("--explorer", action="store_true")
    p.add_argument("--open-browser", action="store_true")
    p.add_argument("--peer", nargs=2, action="append", metavar=("HOST", "PORT"))
    args = p.parse_args()

    db_path = args.db or f"blockchain_node_{args.port}.db"
    procs = []

    if args.explorer:
        env_extra = {"BRN_DB": db_path}
        import os
        env = {**os.environ, **env_extra}
        procs.append(subprocess.Popen([sys.executable, "explorer.py"], env=env))
        time.sleep(1.0)
        if args.open_browser:
            webbrowser.open("http://localhost:8080")

    cmd = [sys.executable, "node.py", str(args.port), db_path]
    if args.miner:
        cmd.append(args.miner)
    if args.mine:
        cmd.append("--mine")

    try:
        subprocess.run(cmd)
    finally:
        for pr in procs:
            pr.terminate()

if __name__ == "__main__":
    main()