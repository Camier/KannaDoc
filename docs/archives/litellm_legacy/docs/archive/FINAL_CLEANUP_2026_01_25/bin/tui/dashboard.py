#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Label, DataTable, Digits
from textual.reactive import reactive
from textual.worker import Worker
import subprocess
import json
import xmltodict
import os
import psutil
import socket

# Configuration des Services
SERVICES = [
    {
        "id": "proxy",
        "name": "LiteLLM Proxy",
        "unit": "litellm.service",
        "port": 4000,
        "type": "systemd",
        "model": "ROUTER (See Config)"
    },
    {
        "id": "ollama",
        "name": "Ollama Server",
        "unit": "ollama.service",
        "port": 11434,
        "type": "systemd",
        "model": "Multi-Model (Mistral, Qwen, etc.)"
    },
    {
        "id": "llamacpp",
        "name": "LlamaCPP (Chat)",
        "script": "bin/ops/start_llamacpp.sh",
        "port": 8002,
        "type": "script",
        "model": "Hermes-3-Llama-3.1-8B"
    },
    {
        "id": "rerank",
        "name": "Rerank Service",
        "unit": "litellm-rerank.service",
        "port": 8079,
        "type": "systemd",
        "model": "Cohere/Rerank-English-v3.0"
    },
    {
        "id": "embed",
        "name": "Embeddings",
        "unit": "litellm-embed-arctic.service",
        "port": 8082,
        "type": "systemd",
        "model": "Snowflake-Arctic-Embed-L"
    }
]

def validate_port(port):
    """
    Validate that a port number is an integer within the valid range (1-65535).
    
    Args:
        port: Port number to validate
        
    Returns:
        int: The validated port number
        
    Raises:
        ValueError: If port is not a valid integer or not in range 1-65535
        TypeError: If port is not an integer or cannot be converted to one
    """
    if isinstance(port, str):
        # Try to convert string to int first
        try:
            port = int(port)
        except ValueError:
            raise ValueError(f"Invalid port: {port!r} - must be a number")
    
    if not isinstance(port, int):
        raise TypeError(f"Invalid port type: {type(port).__name__} - must be an integer")
    
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port} - must be between 1 and 65535")
    
    return port


def check_port(port):
    """Check if a port is open on localhost."""
    port = validate_port(port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def get_gpu_stats():
    try:
        # Fast query for nvidia-smi xml
        result = subprocess.run(['nvidia-smi', '-q', '-x'], capture_output=True, text=True)
        data = xmltodict.parse(result.stdout)
        gpu = data['nvidia_smi_log']['gpu']
        if isinstance(gpu, list): gpu = gpu[0] # Take first GPU if multiple
        
        mem_used = gpu['fb_memory_usage']['used']
        mem_total = gpu['fb_memory_usage']['total']
        util = gpu['utilization']['gpu_util']
        temp = gpu['temperature']['gpu_temp']
        
        return {
            "vram": f"{mem_used} / {mem_total}",
            "util": util,
            "temp": temp
        }
    except:
        return {"vram": "N/A", "util": "0%", "temp": "0C"}


class ServiceRow(Static):
    status = reactive("Checking...")
    
    def __init__(self, service_data):
        super().__init__()
        self.service = service_data
        self.styles.height = 3
        self.styles.margin = (0, 0, 1, 0)
        self.styles.background = "#1e1e1e"
        self.styles.border = ("tall", "blue")

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(classes="info_box"):
                yield Label(f"[b]{self.service['name']}[/b]", classes="service_name")
                yield Label(f"Model: {self.service['model']}", classes="model_name")
            
            yield Label(self.status, id=f"status-{self.service['id']}", classes="status_label")
            
            with Horizontal(classes="buttons"):
                yield Button("Start", variant="success", id=f"start-{self.service['id']}")
                yield Button("Stop", variant="error", id=f"stop-{self.service['id']}")
                yield Button("Restart", variant="warning", id=f"restart-{self.service['id']}")

    def on_mount(self):
        self.set_interval(2, self.update_status)

    def update_status(self):
        is_active = check_port(self.service['port'])
        label = self.query_one(f"#status-{self.service['id']}", Label)
        
        if is_active:
            label.update("● ACTIVE")
            label.styles.color = "green"
            self.styles.border = ("tall", "green")
        else:
            label.update("○ STOPPED")
            label.styles.color = "red"
            self.styles.border = ("tall", "red")

    def on_button_pressed(self, event: Button.Pressed):
        action = event.button.id.split("-")[0]
        self.handle_action(action)

    def handle_action(self, action):
        cmd = []
        if self.service['type'] == 'systemd':
            cmd = ["systemctl", "--user", action, self.service['unit']]
        elif self.service['type'] == 'script':
            if action == "start":
                # Scripts need to be run in background properly, often complex
                # Ideally we wrap scripts in systemd, but for now:
                if self.service['id'] == "llamacpp":
                    cmd = ["bash", "/LAB/@litellm/bin/ops/start_llamacpp.sh"]
            elif action == "stop":
                # Kill by port for script-based services
                port = validate_port(self.service['port'])
                # Use list argument format instead of shell=True to prevent command injection
                subprocess.run(["fuser", "-k", f"{port}/tcp"], check=False)
                return

        if cmd:
            subprocess.Popen(cmd)
            self.notify(f"{action.capitalize()} command sent to {self.service['name']}")


class GPUStatus(Static):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("GPU VRAM:", classes="gpu_label")
            yield Digits("0000MiB", id="vram_digits", classes="gpu_digits")
            yield Label("UTIL:", classes="gpu_label")
            yield Digits("00%", id="util_digits", classes="gpu_digits")

    def on_mount(self):
        self.set_interval(1, self.update_stats)

    def update_stats(self):
        stats = get_gpu_stats()
        self.query_one("#vram_digits", Digits).update(stats['vram'].replace("MiB", ""))
        self.query_one("#util_digits", Digits).update(stats['util'])

class LiteLLMDashboard(App):
    CSS = """
    Screen {
        layout: vertical;
        padding: 1;
        background: #0d1117;
    }
    
    Header {
        dock: top;
        height: 3;
        content-align: center middle;
        background: #161b22;
        color: #58a6ff;
    }

    GPUStatus {
        height: 5;
        margin: 1;
        background: #161b22;
        padding: 1;
        border: solid #30363d;
    }
    
    .gpu_label {
        content-align: center middle;
        height: 100%;
        margin-right: 1;
        color: #8b949e;
    }
    
    .gpu_digits {
        color: #3fb950;
        width: 20;
    }

    ServiceRow {
        height: 5;
        padding: 1;
        border-left: wide #30363d;
        background: #161b22;
        margin-bottom: 1;
    }

    .info_box {
        width: 40;
    }

    .service_name {
        color: #c9d1d9;
        text-style: bold;
    }

    .model_name {
        color: #8b949e;
    }

    .status_label {
        width: 15;
        content-align: center middle;
        text-style: bold;
    }

    .buttons {
        width: 1fr;
        align: right middle;
    }

    Button {
        margin-left: 1;
        min-width: 10;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("  INFRASTRUCTURE STATUS & CONTROL", classes="title")
        yield GPUStatus()
        
        yield Container(
            *[ServiceRow(svc) for svc in SERVICES],
            id="services_container"
        )
        
        yield Footer()

if __name__ == "__main__":
    app = LiteLLMDashboard()
    app.run()
