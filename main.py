"""
main.py
Executor unificado da BRN v2.
Uso:
    python main.py <porta>              -> Inicia nó + explorador + GUI
    python main.py <porta> --miner      -> Nó + explorador + mineração automática
    python main.py <porta> --cli        -> Modo CLI (sem GUI)
"""

import sys
import os
import time
import threading

from bruno_blockchain_v2 import CriptoAPI, COIN_NAME, COIN_SYMBOL
from cripto_wallet_v2 import Wallet, encrypt_wallet, decrypt_wallet


def start_explorer_subprocess(db_path):
    import subprocess
    return subprocess.Popen(
        [sys.executable, "explorer.py", db_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def cli_mode(api, wallet):
    print(f"\n{COIN_NAME} ({COIN_SYMBOL}) - Modo CLI")
    print(f"Carteira: {wallet.address}\n")
    while True:
        cmd = input("brn> ").strip().split()
        if not cmd:
            continue
        if cmd[0] == "status":
            s = api.get_status()
            for k, v in s.items():
                print(f"  {k}: {v}")
        elif cmd[0] == "miner" and len(cmd) > 1 and cmd[1] == "start":
            ok, msg = api.start_mining(wallet.address)
            print(f"  {msg}")
        elif cmd[0] == "miner" and len(cmd) > 1 and cmd[1] == "stop":
            ok, msg = api.stop_mining()
            print(f"  {msg}")
        elif cmd[0] == "balance":
            print(f"  Saldo: {api.get_balance(wallet.address)} BRN")
        elif cmd[0] == "send" and len(cmd) >= 3:
            to_addr, amount = cmd[1], cmd[2]
            tx, msg = api.create_transaction(wallet, to_addr, amount)
            if tx:
                ok, m = api.submit_transaction(tx)
                print(f"  {m}")
            else:
                print(f"  {msg}")
        elif cmd[0] == "chain":
            chain = api.get_full_chain()
            for b in chain[-10:]:
                print(f"  #{b['height']} {b['hash'][:24]}... diff={b['difficulty']}")
        elif cmd[0] == "exit":
            break
        else:
            print("  Comandos: status | miner start | miner stop | balance | send <addr> <amt> | chain | exit")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6001
    api = CriptoAPI(port)

    # Carteira: carrega ou cria
    wallet_path = f"wallets/wallet_{port}.wallet"
    os.makedirs("wallets", exist_ok=True)
    if os.path.exists(wallet_path):
        try:
            pwd = input("Senha da carteira: ")
            wallet = decrypt_wallet(wallet_path, pwd)
        except Exception as e:
            print(f"Erro ao abrir carteira: {e}")
            wallet = Wallet()
    else:
        wallet = Wallet()
        print(f"[CARTEIRA] Nova carteira criada: {wallet.address}")
        try:
            pwd = input("Defina uma senha (mín 12 chars) para backup: ")
            if len(pwd) >= 12:
                encrypt_wallet(wallet, pwd, wallet_path)
                print(f"[CARTEIRA] Backup salvo em {wallet_path}")
        except Exception as e:
            print(f"[CARTEIRA] Backup não salvo: {e}")

    # Injeta a carteira no api (para GUI e CLI)
    api.wallet = wallet
    api.wallet_address = wallet.address

    # Inicia explorador
    db_path = f"brn_v2_chain_{port}.db"
    explorer_proc = start_explorer_subprocess(db_path)
    time.sleep(1)
    print(f"[EXPLORADOR] http://127.0.0.1:8080")

    # Modo CLI
    if "--cli" in sys.argv:
        try:
            cli_mode(api, wallet)
        except KeyboardInterrupt:
            pass
        explorer_proc.terminate()
        api.p2p.stop()
        return

    # Modo mineração automática
    if "--miner" in sys.argv:
        api.start_mining(wallet.address)
        print(f"[MINERAÇÃO] Automática ativa para {wallet.address}")

    # Modo GUI (pywebview)
    try:
        import webview
        html_path = os.path.abspath("index.html")
        window = webview.create_window(
            f"{COIN_NAME} v2 - Nó {port}",
            f"file://{html_path}",
            js_api=api,
            width=1100, height=750
        )
        webview.start()
    except ImportError:
        print("[AVISO] pywebview não instalado. Rodando em modo servidor.")
        print(f"Nó ativo na porta {port}. Use Ctrl+C para sair.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        explorer_proc.terminate()
        api.p2p.stop()


if __name__ == "__main__":
    main()
    