#!/usr/bin/env python3
"""
Blueworks Live MCP Server - エントリーポイント

使用方法:
    python __main__.py

または Bob の mcp.json に登録して自動起動:
    {
      "mcpServers": {
        "blueworks-live": {
          "command": "/path/to/python3",
          "args": ["/path/to/bwl-mcp-server/__main__.py"],
          "env": {
            "BWL_ACCOUNT": "<account>",
            "BWL_CLIENT_ID": "<client_id>",
            "BWL_CLIENT_SECRET": "<client_secret>"
          }
        }
      }
    }
"""

from server import mcp

if __name__ == "__main__":
    mcp.run()
