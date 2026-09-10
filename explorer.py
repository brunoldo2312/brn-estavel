"""
explorer.py
Explorador de blocos da Moeda Bruno v2 (Flask, porta 8080).
"""
from flask import Flask, render_template_string, request
import time
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "brn_v2_chain_6001.db"
PORT = 8080

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Explorador BRN v2</title>
<style>
    body { background: #121212; color: #e0e0e0; font-family: 'Courier New', monospace;
           margin: 0; padding: 20px; }
    h1 { color: #00ffcc; text-align: center; margin-bottom: 5px; }
    .sub { text-align: center; color: #888; margin-bottom: 20px; }
    .stats { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
             margin-bottom: 20px; }
    .stat { background: #1e1e1e; border: 1px solid #333; border-radius: 8px;
            padding: 10px 20px; min-width: 120px; text-align: center; }
    .stat .v { color: #00ffcc; font-size: 1.3em; font-weight: bold; }
    .stat .l { color: #888; font-size: 0.75em; text-transform: uppercase; }
    .card { background: #1e1e1e; border: 1px solid #333; border-radius: 8px;
            padding: 20px; max-width: 1100px; margin: 0 auto 20px; }
    .card h2 { color: #ffaa00; border-bottom: 1px solid #333;
               padding-bottom: 10px; margin-top: 0; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #333;
             word-break: break-all; font-size: 0.9em; }
    th { color: #888; text-transform: uppercase; font-size: 0.75em; }
    tr:hover { background: #2a2a2a; }
    a { color: #00ffcc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .hash { color: #00ffcc; font-size: 0.85em; }
    .footer { text-align: center; color: #555; font-size: 0.8em; margin-top: 30px; }
</style>
</head>
<body>
    <h1>⛓️ Explorador de Blocos - BRN v2</h1>
    <div class="sub">Moeda Bruno (BRN) - Proof of Work + UTXO + Merkle</div>

    <div class="stats">
        <div class="stat"><div class="v">{{ height }}</div><div class="l">Altura</div></div>
        <div class="stat"><div class="v">{{ difficulty }}</div><div class="l">Dificuldade</div></div>
        <div class="stat"><div class="v">{{ reward }}</div><div class="l">Recompensa</div></div>
        <div class="stat"><div class="v">{{ total_mined }}</div><div class="l">Total Minerado</div></div>
        <div class="stat"><div class="v">{{ max_supply }}</div><div class="l">Suprimento Máx</div></div>
    </div>

    <div class="card">
        <h2>Últimos Blocos</h2>
        <table>
            <thead>
                <tr>
                    <th>Altura</th>
                    <th>Hash</th>
                    <th>Merkle Root</th>
                    <th>Timestamp</th>
                    <th>Diff</th>
                    <th>Nonce</th>
                </tr>
            </thead>
            <tbody>
                {% for b in blocks %}
                <tr>
                    <td><a href="/block/{{ b.height }}">{{ b.height }}</a></td>
                    <td class="hash">{{ b.hash[:28] }}...</td>
                    <td class="hash">{{ b.merkle_root[:20] }}...</td>
                    <td>{{ b.ts }}</td>
                    <td>{{ b.difficulty }}</td>
                    <td>{{ b.nonce }}</td>
                </tr>
                {% else %}
                <tr><td colspan="6" style="text-align:center;color:#888;">
                    Nenhum bloco encontrado.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <div class="footer">BRN v2 - Explorador Local</div>
</body>
</html>
"""

BLOCK_HTML = """
<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8">
<title>Bloco {{ block.height }}</title>
<style>
    body { background:#121212; color:#e0e0e0; font-family:'Courier New',monospace;
           padding:20px; }
    h1 { color:#00ffcc; }
    .field { padding:8px 0; border-bottom:1px solid #333; }
    .label { color:#888; display:inline-block; width:180px; }
    .val { color:#00ffcc; word-break:break-all; }
    .tx { background:#1e1e1e; border:1px solid #333; border-radius:6px;
          padding:12px; margin:10px 0; }
    .txid { color:#ffaa00; font-size:0.85em; }
    a { color:#00ffcc; }
</style></head><body>
<h1>Bloco #{{ block.height }}</h1>
<div class="field"><span class="label">Hash:</span><span class="val">{{ block.hash }}</span></div>
<div class="field"><span class="label">Anterior:</span><span class="val">{{ block.previous_hash }}</span></div>
<div class="field"><span class="label">Merkle Root:</span><span class="val">{{ block.merkle_root }}</span></div>
<div class="field"><span class="label">Timestamp:</span><span class="val">{{ ts }}</span></div>
<div class="field"><span class="label">Dificuldade:</span><span class="val">{{ block.difficulty }}</span></div>
<div class="field"><span class="label">Nonce:</span><span class="val">{{ block.nonce }}</span></div>
<h2 style="color:#ffaa00;">Transações ({{ txs|length }})</h2>
{% for t in txs %}
<div class="tx">
    <div class="txid">TXID: {{ t.txid }}</div>
    <div>Coinbase: {{ t.coinbase }} | Taxa: {{ t.fee }} BRN</div>
    <div>Entradas: {{ t.inputs|length }} | Saídas: {{ t.outputs|length }}</div>
    {% for o in t.outputs %}
    <div style="color:#00ffcc;">→ {{ o.address }} : {{ o.amount }} BRN</div>
    {% endfor %}
</div>
{% endfor %}
<p><a href="/">← Voltar</a></p>
</body></html>
"""


def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@app.route("/")
def index():
    blocks_raw = query("SELECT * FROM blocks ORDER BY height DESC LIMIT 20")
    blocks = [{
        "height": b["height"],
        "hash": b["hash"],
        "merkle_root": b["merkle_root"] or "",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(b["timestamp"])),
        "difficulty": b["difficulty"],
        "nonce": b["nonce"],
    } for b in blocks_raw]

    stats = query("""SELECT
        (SELECT MAX(height) FROM blocks) as height,
        (SELECT difficulty FROM blocks ORDER BY height DESC LIMIT 1) as difficulty,
        (SELECT SUM(CAST(amount AS REAL)) FROM utxos) as total
    """)[0]

    return render_template_string(
        HTML,
        blocks=blocks,
        height=stats["height"] or 0,
        difficulty=stats["difficulty"] or 0,
        reward="—",
        total_mined=f"{stats['total']:.4f}" if stats["total"] else "0",
        max_supply="21,000,000"
    )


@app.route("/block/<int:h>")
def block_detail(h):
    blocks = query("SELECT * FROM blocks WHERE height=?", (h,))
    if not blocks:
        return "Bloco não encontrado", 404
    block = blocks[0]
    txs = query("SELECT raw FROM transactions WHERE block_height=? ORDER BY rowid", (h,))
    import json as _json
    tx_list = [_json.loads(t["raw"]) for t in txs]
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block["timestamp"]))
    return render_template_string(BLOCK_HTML, block=block, txs=tx_list, ts=ts)


if __name__ == "__main__":
    print(f"[EXPLORADOR] Iniciando em http://127.0.0.1:{PORT}")
    print(f"[EXPLORADOR] Banco: {DB_PATH}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)