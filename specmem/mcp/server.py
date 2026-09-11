"""SpecMem MCP Server implementation.

Provides the main MCP server class that handles tool calls
from Kiro and routes them to appropriate handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from specmem.mcp.handlers import ToolHandlers
from specmem.mcp.tools import TOOLS, get_tool_names


logger = logging.getLogger(__name__)


class SpecMemMCPServer:
    """MCP server exposing SpecMem tools to Kiro.

    This server implements the Model Context Protocol to expose
    SpecMem functionality as tools that Kiro can invoke.

    Example:
        server = SpecMemMCPServer(workspace_path=Path("."))
        await server.initialize()
        result = await server.handle_tool_call("specmem_query", {"query": "auth"})
    """

    def __init__(self, workspace_path: Path | str = "."):
        """Initialize the MCP server.

        Args:
            workspace_path: Path to the workspace root
        """
        self.workspace_path = Path(workspace_path).resolve()
        self._handlers = ToolHandlers()
        self._initialized = False

    async def initialize(self) -> dict[str, Any]:
        """Initialize the spec memory for the workspace.

        Creates or loads the SpecMemClient for the workspace.

        Returns:
            Dict with initialization status
        """
        if self._initialized:
            return {
                "status": "already_initialized",
                "workspace": str(self.workspace_path),
            }

        try:
            # Import here to avoid circular imports
            from specmem.client import SpecMemClient

            client = SpecMemClient(path=self.workspace_path)
            self._handlers.set_client(client)
            self._initialized = True

            logger.info(f"SpecMem initialized for {self.workspace_path}")

            return {
                "status": "initialized",
                "workspace": str(self.workspace_path),
            }
        except Exception as e:
            logger.error(f"Failed to initialize SpecMem: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to initialize SpecMem. Run 'specmem init' first.",
            }

    @property
    def is_initialized(self) -> bool:
        """Check if the server is initialized."""
        return self._initialized

    def get_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools.

        Returns:
            List of tool definitions
        """
        return TOOLS.copy()

    def get_tool_names(self) -> list[str]:
        """Get list of tool names.

        Returns:
            List of tool name strings
        """
        return get_tool_names()

    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a tool call from Kiro.

        Routes the call to the appropriate handler based on tool name.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result as a dict
        """
        # Auto-initialize if not already done
        if not self._initialized:
            init_result = await self.initialize()
            if init_result.get("status") == "error":
                return {
                    "error": "not_initialized",
                    "message": init_result.get("message", "SpecMem not initialized"),
                }

        # Route to appropriate handler
        handler_map = {
            "specmem_query": self._handlers.handle_query,
            "specmem_impact": self._handlers.handle_impact,
            "specmem_context": self._handlers.handle_context,
            "specmem_tldr": self._handlers.handle_tldr,
            "specmem_cues": self._handlers.handle_cues,
            "specmem_coverage": self._handlers.handle_coverage,
            "specmem_validate": self._handlers.handle_validate,
        }

        handler = handler_map.get(tool_name)
        if handler is None:
            return {
                "error": "unknown_tool",
                "message": f"Unknown tool: {tool_name}",
                "available_tools": list(handler_map.keys()),
            }

        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {
                "error": "tool_error",
                "tool": tool_name,
                "message": str(e),
            }


async def run_stdio_server(workspace_path: Path | str = ".") -> None:
    """Run the MCP server using stdio transport.

    This is the entry point for the specmem-mcp command.

    Args:
        workspace_path: Path to the workspace root
    """
    server = SpecMemMCPServer(workspace_path=workspace_path)

    # Read from stdin, write to stdout
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(
        writer_transport, writer_protocol, reader, asyncio.get_event_loop()
    )

    logger.info("SpecMem MCP server started")

    while True:
        try:
            line = await reader.readline()
            if not line:
                break

            request = json.loads(line.decode())
            method = request.get("method", "")

            if method == "initialize":
                response = await server.initialize()
            elif method == "tools/list":
                response = {"tools": server.get_tools()}
            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                response = await server.handle_tool_call(tool_name, arguments)
            else:
                response = {"error": "unknown_method", "method": method}

            # Write response
            response_json = json.dumps({"id": request.get("id"), "result": response})
            writer.write((response_json + "\n").encode())
            await writer.drain()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Server error: {e}")


def main() -> None:
    """Main entry point for specmem-mcp command."""
    import argparse

    parser = argparse.ArgumentParser(description="SpecMem MCP Server")
    parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        default=".",
        help="Workspace path (default: current directory)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(run_stdio_server(workspace_path=args.workspace))


if __name__ == "__main__":
    main()
