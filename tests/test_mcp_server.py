import pytest
from core.mcp.server import FPNexusMCPServer

def test_mcp_initialize():
    server = FPNexusMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    resp = server.handle_request(req)
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "fp-nexus-agent"

def test_mcp_tools_list():
    server = FPNexusMCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    resp = server.handle_request(req)
    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "optimize_gig" in tool_names
    assert "draft_proposal" in tool_names
    assert "audit_gig_seo" in tool_names
    assert "format_portfolio_project" in tool_names
    assert "reply_to_client" in tool_names
    assert "scan_competitor_gig" in tool_names
    assert "get_freelance_receipts" in tool_names
    assert "run_biweekly_seo_audit" in tool_names
