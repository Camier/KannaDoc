# Ops Dashboard (TUI)

This repo ships a local **Textual TUI** dashboard at `bin/tui/dashboard.py`.
It runs in your terminal and checks localhost ports; it is **not** exposed via HTTP
and there is no `/dashboard` route in `config.yaml`.

## Run
```bash
python3 bin/tui/dashboard.py
```

## What it shows
- Port status for local services (proxy, Ollama, rerank, embeddings, llama.cpp).
- Basic host telemetry (GPU stats if `nvidia-smi` is available).
- Start/stop/restart actions for **systemd** units when present.

## Requirements
- Python packages: `textual`, `psutil`, `xmltodict`.
- Designed for **host/systemd** usage. In Docker-only setups, systemd controls
  will not work, but port checks still do.

## Notes
- This UI does not expose secrets; it only reports service status.
