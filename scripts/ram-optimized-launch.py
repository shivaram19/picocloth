#!/usr/bin/env python3
"""
RAM-Optimized PicoCloth Fleet Launcher
Optimizes all 10 node configs for low memory footprint, then launches the fleet.

System: 16GB RAM, ~5GB available, 4 CPU cores
Strategy:
- context_window: 2M -> 32K (~60x reduction)
- max_tokens: 32K -> 2K
- max_tool_iterations: 15 -> 3
- log_level: info -> warn
- max_connections: 100 -> 5
- Disable hooks on non-essential nodes (saves 2 Python processes per node)
- Disable MCP on non-essential nodes
- Only Node-A and Node-B keep full hooks + MCP
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PICOCLOTH_DIR = Path("/home/shivaramgoud/tinkering/tinkering-with-claws/picocloth")
PICOCLAW_BINARY = "/tmp/picoclaw/picoclaw"
NODES = ["node-a", "node-b", "node-c", "node-d", "node-e",
         "node-f", "node-g", "node-h", "node-i", "node-j"]
PORTS = [18790, 18791, 18792, 18793, 18794, 18795, 18796, 18797, 18798, 18799]

# Role definitions for each node
ROLES = {
    "node-a": {"model": "grok-4.20-reasoning", "prompt": "Curiosity Brain - Research & query construction docs", "hooks": True, "mcp": True},
    "node-b": {"model": "grok-4.1-fast", "prompt": "Executor Builder - Run backend, draft RFIs, deploy", "hooks": True, "mcp": True},
    "node-c": {"model": "grok-4.1-fast", "prompt": "Memory Guardian - Archive facts, maintain knowledge graph", "hooks": False, "mcp": False},
    "node-d": {"model": "grok-4.1-fast", "prompt": "Safety Auditor - Scan uploads, enforce budget, validate inputs", "hooks": False, "mcp": False},
    "node-e": {"model": "grok-4.1-fast", "prompt": "Document Parser - Extract text from PDFs, specs, drawings", "hooks": False, "mcp": False},
    "node-f": {"model": "grok-4.1-fast", "prompt": "Contradiction Detector - Find spec-drawing mismatches", "hooks": False, "mcp": False},
    "node-g": {"model": "grok-4.1-fast", "prompt": "RFI Drafter - Generate professional cited RFI responses", "hooks": False, "mcp": False},
    "node-h": {"model": "grok-4.1-fast", "prompt": "Knowledge Graph Builder - Extract entities & relationships", "hooks": False, "mcp": False},
    "node-i": {"model": "grok-4.1-fast", "prompt": "Fleet Router - Classify tasks, delegate, load balance", "hooks": False, "mcp": False},
    "node-j": {"model": "grok-4.1-fast", "prompt": "Metrics Collector - Track tokens, latency, costs, alerts", "hooks": False, "mcp": False},
}

XAI_KEY = os.environ.get("XAI_API_KEY", "xai-YOUR_API_KEY_HERE")

def log(msg, color=""):
    colors = {
        "blue": "\033[0;34m", "green": "\033[0;32m",
        "yellow": "\033[1;33m", "red": "\033[0;31m",
        "cyan": "\033[0;36m", "magenta": "\033[0;35m",
        "nc": "\033[0m"
    }
    prefix = colors.get(color, "")
    suffix = colors.get("nc", "")
    print(f"{prefix}[RAM-OPT]{suffix} {msg}")

def backup_configs():
    backup_dir = PICOCLOTH_DIR / "backups" / "ram-opt-originals"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for node in NODES:
        src = PICOCLOTH_DIR / node / "config.json"
        dst = backup_dir / f"{node}-config.json.orig"
        if src.exists():
            shutil.copy2(src, dst)
    log(f"Backed up all 10 node configs to {backup_dir}", "green")

def generate_optimized_config(node_id: str, port: int) -> dict:
    role = ROLES[node_id]
    enable_hooks = role["hooks"]
    enable_mcp = role["mcp"]

    base = {
        "version": 1,
        "agents": {
            "defaults": {
                "workspace": str(PICOCLOTH_DIR / node_id / "workspace"),
                "restrict_to_workspace": False,
                "model_name": role["model"],
                "max_tokens": 2048,
                "max_tool_iterations": 3,
                "context_window": 32768,
                "steering_mode": "one-at-a-time",
                "system_prompt": f"You are {node_id.upper().replace('-','-')}, the {role['prompt']}. RAM-optimized mode: concise responses, minimal tool calls.",
                "routing": {
                    "enabled": True,
                    "light_model": "grok-4.1-fast",
                    "threshold": 0.4
                }
            }
        },
        "channel_list": {
            "pico": {
                "enabled": True,
                "type": "pico",
                "settings": {
                    "ping_interval": 30,
                    "read_timeout": 60,
                    "write_timeout": 10,
                    "max_connections": 5,
                    "token": f"fleet-token-{node_id}"
                }
            }
        },
        "model_list": [
            {
                "model_name": "grok-4.20-reasoning",
                "provider": "openai",
                "model": "grok-4.20-0309-reasoning",
                "api_base": "https://api.x.ai/v1",
                "api_keys": [XAI_KEY],
                "enabled": True
            },
            {
                "model_name": "grok-4.1-fast",
                "provider": "openai",
                "model": "grok-4-1-fast-non-reasoning",
                "api_base": "https://api.x.ai/v1",
                "api_keys": [XAI_KEY],
                "enabled": True
            }
        ],
        "gateway": {
            "host": "127.0.0.1",
            "port": port,
            "log_level": "warn"
        },
        "heartbeat": {
            "enabled": True,
            "interval": 30
        },
        "hooks": {
            "enabled": enable_hooks,
            "processes": {}
        },
        "tools": {
            "web": {"enabled": True, "provider": "duckduckgo"},
            "mcp": {
                "enabled": enable_mcp,
                "servers": {
                    "fleet_server": {
                        "enabled": enable_mcp,
                        "command": "python3",
                        "args": [str(PICOCLOTH_DIR / "mcp-fleet-server" / "server.py")],
                        "env": {
                            "FLEET_NODE_ID": node_id,
                            "FLEET_SHARED_DIR": str(PICOCLOTH_DIR / "shared")
                        }
                    }
                } if enable_mcp else {}
            }
        }
    }

    # Add hooks only for node-a and node-b (lightweight version)
    if enable_hooks:
        base["hooks"]["processes"] = {
            "digital_twin_guardian": {
                "enabled": True,
                "priority": 1,
                "command": [str(PICOCLOTH_DIR / ".venv" / "bin" / "python3"), str(PICOCLOTH_DIR / "hooks" / "digital_twin_guardian.py")],
                "env": {
                    "FLEET_NODE_ID": node_id,
                    "PICOCLAW_HOOK_TWIN_DIR": str(PICOCLOTH_DIR / "shared" / "digital-twins" / node_id),
                    "PICOCLAW_HOOK_PROJECT_DIR": str(PICOCLOTH_DIR / "shared" / "project"),
                    "PICOCLAW_HOOK_MAX_FACTS": "4"
                },
                "observe": ["turn_end", "context_compress"]
            }
        }
        # Skip langfuse hook to save RAM

    return base

def install_configs():
    for i, node in enumerate(NODES):
        port = PORTS[i]
        config = generate_optimized_config(node, port)
        config_path = PICOCLOTH_DIR / node / "config.json"
        home_config_path = PICOCLOTH_DIR / node / "home" / "config.json"
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        (PICOCLOTH_DIR / node / "home").mkdir(parents=True, exist_ok=True)
        with open(home_config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        hooks_status = "🪝" if ROLES[node]["hooks"] else "⛔"
        mcp_status = "🔌" if ROLES[node]["mcp"] else "⛔"
        log(f"{node} port={port} ctx=32K maxtok=2K iter=3 {hooks_status}hooks {mcp_status}mcp", "cyan")

    log("All 10 RAM-optimized configs installed", "green")

def stop_existing():
    log("Stopping any existing picoclaw processes...", "yellow")
    subprocess.run(["pkill", "-f", "picoclaw gateway"], capture_output=True)
    time.sleep(1)
    # Clean up PID files
    for node in NODES:
        pid_file = PICOCLOTH_DIR / node / "pid"
        if pid_file.exists():
            pid_file.unlink()
    log("Existing processes cleaned up", "green")

def launch_node(node_id: str):
    node_dir = PICOCLOTH_DIR / node_id
    home_dir = node_dir / "home"
    workspace = node_dir / "workspace"
    log_file = node_dir / "node.log"
    
    home_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Set minimal hook env
    env = os.environ.copy()
    env["PICOCLAW_HOME"] = str(home_dir)
    env["PICOCLAW_HOOK_TWIN_DIR"] = str(PICOCLOTH_DIR / "shared" / "digital-twins" / node_id)
    env["PICOCLAW_HOOK_PROJECT_DIR"] = str(PICOCLOTH_DIR / "shared" / "project")
    env["PICOCLAW_HOOK_NODE_ID"] = node_id
    env["PICOCLAW_HOOK_MAX_FACTS"] = "4"
    
    # Clear old log
    log_file.write_text("")
    
    proc = subprocess.Popen(
        [PICOCLAW_BINARY, "gateway"],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        cwd=str(node_dir),
        env=env,
        start_new_session=True
    )
    
    pid_file = node_dir / "pid"
    pid_file.write_text(str(proc.pid))
    return proc.pid

def launch_fleet():
    log("Launching RAM-optimized 10-node fleet...", "blue")
    pids = {}
    for node in NODES:
        pid = launch_node(node)
        pids[node] = pid
        log(f"{node} launched (PID: {pid})", "green")
        time.sleep(0.3)  # Stagger to avoid thundering herd
    
    return pids

def check_memory():
    """Return total RSS of all picoclaw processes in MB."""
    try:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-C", "picoclaw"],
            capture_output=True, text=True
        )
        total_kb = sum(int(x) for x in result.stdout.strip().split() if x.strip().isdigit())
        return total_kb / 1024
    except Exception:
        return 0.0

def show_dashboard(pids: dict):
    time.sleep(2)
    mem_mb = check_memory()
    
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║     🚀 RAM-OPTIMIZED PICO CLOTH 10-NODE FLEET                                ║")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    print("║                                                                              ║")
    for i, node in enumerate(NODES):
        port = PORTS[i]
        pid = pids.get(node, "?")
        role = ROLES[node]["prompt"][:40]
        print(f"║  {node:8} │ port {port} │ PID {pid:6} │ {role:40} ║")
    print("║                                                                              ║")
    print(f"║  💾 Fleet Memory: ~{mem_mb:.0f} MB total RSS                                ║")
    print(f"║  🧠 Per-Node: context=32K, max_tokens=2K, max_iterations=3, log=warn        ║")
    print(f"║  🔌 Hooks: only node-a, node-b (lightweight)                                ║")
    print(f"║  🔌 MCP: only node-a, node-b                                                ║")
    print("║                                                                              ║")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    print("║  COMMANDS:                                                                   ║")
    print("║    python3 scripts/ram-optimized-launch.py status    # Check health         ║")
    print("║    python3 scripts/ram-optimized-launch.py stop      # Stop fleet           ║")
    print("║    python3 scripts/ram-optimized-launch.py restore   # Restore originals    ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()

def check_status():
    print("\n🩺 Fleet Health Check")
    print("=" * 50)
    total_mem = 0.0
    for i, node in enumerate(NODES):
        port = PORTS[i]
        pid_file = PICOCLOTH_DIR / node / "pid"
        status = "🔴 offline"
        mem = "0 MB"
        
        if pid_file.exists():
            pid = pid_file.read_text().strip()
            # Check if process exists
            if Path(f"/proc/{pid}").exists():
                try:
                    rss = Path(f"/proc/{pid}/statm").read_text().split()[1]
                    rss_mb = int(rss) * 4096 / 1024 / 1024
                    total_mem += rss_mb
                    mem = f"{rss_mb:.1f} MB"
                    
                    # Quick port check
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://127.0.0.1:{port}"],
                        capture_output=True, text=True, timeout=2
                    )
                    if result.stdout.strip() in ("200", "404"):
                        status = f"🟢 online ({mem})"
                    else:
                        status = f"🟡 starting ({mem})"
                except Exception:
                    status = "🟡 unknown"
            else:
                status = "🔴 dead"
        
        print(f"  {node:8} port={port} {status}")
    
    print(f"\n💾 Total Fleet RSS: {total_mem:.1f} MB")
    print(f"🧠 System Available: {get_available_ram():.1f} MB")

def get_available_ram():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    return int(line.split()[1]) / 1024
    except Exception:
        return 0.0
    return 0.0

def stop_fleet():
    log("Stopping fleet...", "yellow")
    for node in NODES:
        pid_file = PICOCLOTH_DIR / node / "pid"
        if pid_file.exists():
            pid = pid_file.read_text().strip()
            try:
                os.kill(int(pid), 15)  # SIGTERM
                log(f"Sent SIGTERM to {node} (PID: {pid})", "blue")
            except ProcessLookupError:
                pass
            pid_file.unlink()
    time.sleep(1)
    # Force kill any stragglers
    subprocess.run(["pkill", "-9", "-f", "picoclaw gateway"], capture_output=True)
    log("Fleet stopped", "green")

def restore_originals():
    backup_dir = PICOCLOTH_DIR / "backups" / "ram-opt-originals"
    if not backup_dir.exists():
        log("No backups found!", "red")
        return
    for node in NODES:
        src = backup_dir / f"{node}-config.json.orig"
        if src.exists():
            shutil.copy2(src, PICOCLOTH_DIR / node / "config.json")
            shutil.copy2(src, PICOCLOTH_DIR / node / "home" / "config.json")
    log("Original configs restored", "green")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "launch"
    
    if cmd == "launch":
        stop_existing()
        backup_configs()
        install_configs()
        pids = launch_fleet()
        show_dashboard(pids)
        log("Fleet launched! Nodes initializing...", "green")
        
    elif cmd == "stop":
        stop_fleet()
        
    elif cmd == "status":
        check_status()
        
    elif cmd == "restore":
        restore_originals()
        
    elif cmd == "backup":
        backup_configs()
        
    else:
        print(f"Usage: {sys.argv[0]} {{launch|stop|status|restore|backup}}")
        print("")
        print("Commands:")
        print("  launch   Backup configs, install RAM-optimized versions, start fleet")
        print("  stop     Stop all picoclaw processes")
        print("  status   Check fleet health and memory usage")
        print("  restore  Restore original configs from backup")
        print("  backup   Just backup current configs")

if __name__ == "__main__":
    main()
