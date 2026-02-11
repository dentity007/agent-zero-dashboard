#!/usr/bin/env python3
"""Agent Zero Status Page — lightweight system monitor."""

import json
import subprocess
import time
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8081


def run_cmd(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def get_docker_status():
    raw = run_cmd('sg docker -c "docker ps --filter name=agent-zero --format \'{{.Status}}\\t{{.Ports}}\'"')
    if not raw:
        return {"running": False, "status": "Not running", "ports": ""}
    parts = raw.split("\t")
    return {"running": True, "status": parts[0], "ports": parts[1] if len(parts) > 1 else ""}


def get_ollama_loaded():
    try:
        req = urllib.request.Request("http://localhost:11434/api/ps")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        models = []
        for m in data.get("models", []):
            models.append({
                "name": m["name"],
                "vram_gb": round(m.get("size_vram", 0) / 1e9, 1),
                "total_gb": round(m.get("size", 0) / 1e9, 1),
                "ctx": m.get("context_length", 0),
                "quantization": m.get("details", {}).get("quantization_level", ""),
                "params": m.get("details", {}).get("parameter_size", ""),
            })
        return models
    except Exception:
        return []


def get_ollama_models():
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        models = []
        for m in data.get("models", []):
            models.append({
                "name": m["name"],
                "size_gb": round(m.get("size", 0) / 1e9, 1),
                "params": m.get("details", {}).get("parameter_size", ""),
                "quantization": m.get("details", {}).get("quantization_level", ""),
            })
        return models
    except Exception:
        return []


def get_gpu_stats():
    raw = run_cmd("nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits")
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) < 5:
        return None
    return {
        "name": parts[0],
        "vram_used": int(parts[1]),
        "vram_total": int(parts[2]),
        "gpu_util": int(parts[3]),
        "temp": int(parts[4]),
        "vram_pct": round(int(parts[1]) / int(parts[2]) * 100, 1),
    }


def get_ram_stats():
    raw = run_cmd("free -m")
    if not raw:
        return None
    for line in raw.split("\n"):
        if line.startswith("Mem:"):
            parts = line.split()
            total = int(parts[1])
            used = int(parts[2])
            return {"total_gb": round(total / 1024, 1), "used_gb": round(used / 1024, 1), "pct": round(used / total * 100, 1)}
    return None


def get_disk_stats():
    raw = run_cmd("df -BG /home --output=size,used,avail,pcent | tail -1")
    if not raw:
        return None
    parts = raw.split()
    if len(parts) < 4:
        return None
    return {
        "total": parts[0],
        "used": parts[1],
        "avail": parts[2],
        "pct": parts[3],
    }


def status_dot(ok):
    color = "#22c55e" if ok else "#ef4444"
    return f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:6px"></span>'


def bar_html(pct, label="", color="#3b82f6"):
    bg = "#1e293b"
    return f'''<div style="background:{bg};border-radius:6px;height:22px;position:relative;overflow:hidden;margin:4px 0">
        <div style="background:{color};height:100%;width:{pct}%;border-radius:6px;transition:width 0.5s"></div>
        <span style="position:absolute;top:2px;left:8px;font-size:12px;color:#e2e8f0">{label}</span>
    </div>'''


def build_page():
    docker = get_docker_status()
    loaded = get_ollama_loaded()
    all_models = get_ollama_models()
    gpu = get_gpu_stats()
    ram = get_ram_stats()
    disk = get_disk_stats()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    # Loaded models rows
    loaded_rows = ""
    for m in loaded:
        loaded_rows += f"<tr><td>{m['name']}</td><td>{m['params']}</td><td>{m['vram_gb']} GB</td><td>{m['quantization']}</td><td>{m['ctx']}</td></tr>"
    if not loaded_rows:
        loaded_rows = '<tr><td colspan="5" style="color:#94a3b8">No models loaded</td></tr>'

    # All models rows
    all_rows = ""
    loaded_names = {m["name"] for m in loaded}
    for m in all_models:
        badge = ' <span style="background:#22c55e;color:#000;padding:1px 6px;border-radius:4px;font-size:11px">LOADED</span>' if m["name"] in loaded_names else ""
        all_rows += f"<tr><td>{m['name']}{badge}</td><td>{m['params']}</td><td>{m['size_gb']} GB</td><td>{m['quantization']}</td></tr>"

    # GPU section
    gpu_html = ""
    if gpu:
        vram_color = "#22c55e" if gpu["vram_pct"] < 70 else "#eab308" if gpu["vram_pct"] < 90 else "#ef4444"
        gpu_html = f"""
        <div class="card">
            <h2>GPU — {gpu['name']}</h2>
            <div class="stat-row"><span>VRAM</span><span>{gpu['vram_used']} / {gpu['vram_total']} MiB ({gpu['vram_pct']}%)</span></div>
            {bar_html(gpu['vram_pct'], f"{gpu['vram_used']} / {gpu['vram_total']} MiB", vram_color)}
            <div class="stat-row"><span>GPU Utilization</span><span>{gpu['gpu_util']}%</span></div>
            {bar_html(gpu['gpu_util'], f"{gpu['gpu_util']}%")}
            <div class="stat-row"><span>Temperature</span><span>{gpu['temp']}°C</span></div>
        </div>"""

    # RAM section
    ram_html = ""
    if ram:
        ram_color = "#22c55e" if ram["pct"] < 70 else "#eab308" if ram["pct"] < 90 else "#ef4444"
        ram_html = f"""
        <div class="card">
            <h2>System RAM</h2>
            <div class="stat-row"><span>Used</span><span>{ram['used_gb']} / {ram['total_gb']} GB ({ram['pct']}%)</span></div>
            {bar_html(ram['pct'], f"{ram['used_gb']} / {ram['total_gb']} GB", ram_color)}
        </div>"""

    # Disk section
    disk_html = ""
    if disk:
        disk_html = f"""
        <div class="card">
            <h2>Disk (/home)</h2>
            <div class="stat-row"><span>Used</span><span>{disk['used']} / {disk['total']} ({disk['pct']})</span></div>
            <div class="stat-row"><span>Available</span><span>{disk['avail']}</span></div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Agent Zero Status</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0f172a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }}
        h1 {{ font-size: 24px; margin-bottom: 20px; color: #f8fafc; }}
        h2 {{ font-size: 16px; margin-bottom: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 16px; max-width: 1200px; margin: 0 auto; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
        .card-wide {{ grid-column: 1 / -1; }}
        .stat-row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ text-align: left; padding: 8px; color: #94a3b8; border-bottom: 1px solid #334155; font-weight: 500; }}
        td {{ padding: 8px; border-bottom: 1px solid #1e293b; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto 20px; }}
        .timestamp {{ color: #64748b; font-size: 13px; }}
        .status-badge {{ display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; }}
        .status-up {{ background: #052e16; color: #22c55e; border: 1px solid #166534; }}
        .status-down {{ background: #450a0a; color: #ef4444; border: 1px solid #991b1b; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Agent Zero Status</h1>
        <div>
            <span class="status-badge {'status-up' if docker['running'] else 'status-down'}">
                {status_dot(docker['running'])} Container: {docker['status']}
            </span>
            <span class="timestamp" style="margin-left:12px">Updated: {ts}</span>
        </div>
    </div>
    <div class="grid">
        <div class="card">
            <h2>Loaded Models (VRAM)</h2>
            <table>
                <tr><th>Model</th><th>Params</th><th>VRAM</th><th>Quant</th><th>Context</th></tr>
                {loaded_rows}
            </table>
        </div>
        {gpu_html}
        {ram_html}
        {disk_html}
        <div class="card card-wide">
            <h2>All Ollama Models (on disk)</h2>
            <table>
                <tr><th>Model</th><th>Params</th><th>Size</th><th>Quant</th></tr>
                {all_rows}
            </table>
        </div>
    </div>
</body>
</html>"""


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(build_page().encode())

    def log_message(self, format, *args):
        pass  # suppress request logs


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), StatusHandler)
    print(f"Status page running at http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
