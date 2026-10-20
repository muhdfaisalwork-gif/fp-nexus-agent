#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FP Nexus Agent - Model Context Protocol (MCP) Stdio Entrypoint
Use this file in claude_desktop_config.json, Cursor, Windsurf, or Antigravity.

Example configuration for Claude Desktop:
{
  "mcpServers": {
    "fp-nexus": {
      "command": "python",
      "args": ["G:\\Fiverr and other platforms agent\\run_mcp.py"]
    }
  }
}
"""

import sys
import os

# Ensure UTF-8 on Windows stdout/stdin
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stdin, 'reconfigure'):
    try:
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.mcp.server import run_stdio_server

if __name__ == "__main__":
    run_stdio_server()
