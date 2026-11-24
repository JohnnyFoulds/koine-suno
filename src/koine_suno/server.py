"""MCP server (stdio transport): ``koine-suno-mcp``.

Exposes the same conversions as the CLI as three MCP tools.
"""

from __future__ import annotations

try:  # MCP Python SDK 2.x renamed FastMCP to MCPServer.
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from .ipa import to_ipa
from .suno import SunoOptions, breakdown, to_suno

mcp = _Server("koine-suno")


@mcp.tool()
def koine_to_suno(text: str, y: str = "ü", keep_h: bool = False) -> str:
    """Respell Koine Greek so Suno sings its first-century pronunciation.

    Accepts polytonic or monotonic Greek; line breaks are preserved.
    Stressed syllables are capitalised and syllables hyphenated.

    Args:
        text: Greek text.
        y: spelling for /y/ (υ, οι): "ü" (default), "ee" or "ew".
        keep_h: sing rough breathing as "h".
    """
    return to_suno(text, SunoOptions(y=y, keep_h=keep_h))


@mcp.tool()
def koine_ipa(text: str) -> str:
    """Transcribe Koine Greek to first-century CE (Egyptian) IPA.

    Output matches Wiktionary's Module:grc-pronunciation, period koi1.
    """
    return to_ipa(text)


@mcp.tool()
def koine_breakdown(text: str, y: str = "ü") -> list[dict]:
    """Per-word rows of Greek, first-century IPA and Suno spelling."""
    return breakdown(text, SunoOptions(y=y))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
