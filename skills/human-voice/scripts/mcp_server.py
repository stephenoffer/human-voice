#!/usr/bin/env python3
"""human-voice as an MCP server (stdio). Standard library only.

Register it in any MCP client with the command `python3` and the argument
`<path-to>/skills/human-voice/scripts/mcp_server.py`. See the README for
per-client configuration.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from human_voice_llm.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
