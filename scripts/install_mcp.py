#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1-Click Auto-Installer for FP Nexus Agent MCP Server
Automatically registers the MCP server in Claude Desktop config and displays Cursor instructions.
"""

import os
import sys
import json
import platform

def install_claude_desktop():
    print("=" * 60)
    print("  FP Nexus Agent - MCP Server Auto-Installer")
    print("=" * 60)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_mcp_path = os.path.join(repo_root, "run_mcp.py")
    python_exe = sys.executable

    # Detect OS config path for Claude Desktop
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        config_path = os.path.join(appdata, "Claude", "claude_desktop_config.json")
    elif system == "Darwin": # macOS
        config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
    else: # Linux
        config_path = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")

    print(f"\n[1] Detecting Claude Desktop configuration: {config_path}")

    config_data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            print("    -> Found existing Claude Desktop configuration.")
        except Exception as e:
            print(f"    -> Warning: Could not parse existing config ({e}), creating backup.")
            backup_path = config_path + ".bak"
            try:
                os.rename(config_path, backup_path)
            except Exception:
                pass
            config_data = {}
    else:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        print("    -> Configuration file does not exist yet. Creating fresh configuration.")

    if "mcpServers" not in config_data:
        config_data["mcpServers"] = {}

    config_data["mcpServers"]["fp-nexus"] = {
        "command": python_exe,
        "args": [run_mcp_path]
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        print("    -> SUCCESS: Added 'fp-nexus' to Claude Desktop config!")
    except Exception as e:
        print(f"    -> ERROR writing config: {e}")

    print("\n" + "=" * 60)
    print("  Cursor IDE Configuration Instructions:")
    print("=" * 60)
    print("1. Open Cursor Settings -> Features -> MCP Servers")
    print("2. Click '+ Add New MCP Server'")
    print("3. Name: fp-nexus")
    print("4. Type: command")
    print(f"5. Command: {python_exe} \"{run_mcp_path}\"")
    print("=" * 60)
    print("\nMCP server is ready to use with all freelance tools!\n")

if __name__ == "__main__":
    install_claude_desktop()
