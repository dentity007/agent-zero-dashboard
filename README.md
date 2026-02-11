# Agent Zero Status Dashboard

A lightweight, self-contained status page for monitoring [Agent Zero](https://github.com/frdel/agent-zero) deployments. Single Python file, zero dependencies — just run it.

## What It Shows

- **Docker Container Status** — whether the Agent Zero container is running, uptime, and port mappings
- **Loaded Models (VRAM)** — which Ollama models are currently loaded in GPU memory, with VRAM usage, quantization level, and context length
- **GPU Stats** — VRAM usage bar, GPU utilization, temperature (NVIDIA GPUs via `nvidia-smi`)
- **System RAM** — memory usage with color-coded bar (green/yellow/red)
- **Disk Usage** — total, used, and available space on `/home`
- **All Ollama Models** — every model on disk with a "LOADED" badge for active ones

The page auto-refreshes every 30 seconds. Dark theme, responsive grid layout.

## Requirements

- Python 3.6+ (uses only the standard library — no `pip install` needed)
- NVIDIA GPU with `nvidia-smi` installed (for GPU stats)
- [Ollama](https://ollama.com) running on `localhost:11434` (for model info)
- Docker (for container status)

## Usage

```bash
# Start the status page
python3 status_page.py

# Runs on http://0.0.0.0:8081 by default
```

To change the port, edit the `PORT` variable at the top of `status_page.py`.

### Run as a systemd service

```bash
# Create a service file
sudo tee /etc/systemd/system/agent-zero-status.service << 'EOF'
[Unit]
Description=Agent Zero Status Page
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/bin/python3 /path/to/status_page.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now agent-zero-status
```

## Customization

The dashboard is a single file with inline HTML/CSS. To customize:

- **Port**: Change `PORT = 8081` at the top
- **Refresh interval**: Change `content="30"` in the `<meta http-equiv="refresh">` tag
- **Docker container name**: Change the `--filter name=agent-zero` in `get_docker_status()`
- **Ollama endpoint**: Change `localhost:11434` in `get_ollama_loaded()` and `get_ollama_models()`
- **Disk mount**: Change `/home` in `get_disk_stats()` to monitor a different mount point

## License

MIT
