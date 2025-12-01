"""Web server for SpecMem UI."""

import asyncio
import logging
import socket
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rich.console import Console

from specmem.core.specir import SpecBlock
from specmem.ui import api


logger = logging.getLogger(__name__)
console = Console()


def is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def find_available_port(preferred: int, max_attempts: int = 10) -> int:
    """Find an available port starting from preferred.

    Args:
        preferred: The preferred port to try first
        max_attempts: Maximum number of ports to try

    Returns:
        An available port number

    Raises:
        RuntimeError: If no available port is found
    """
    for offset in range(max_attempts):
        port = preferred + offset
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available port found near {preferred}")


class ConnectionManager:
    """Manage WebSocket connections for live updates."""

    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)


class WebServer:
    """FastAPI-based web server for SpecMem UI."""

    def __init__(
        self,
        blocks: list[SpecBlock],
        port: int = 8765,
        vector_store=None,
        pack_builder=None,
        workspace_path: Path = Path(),
    ):
        """Initialize the web server.

        Args:
            blocks: List of SpecBlocks to serve
            port: Port to listen on (default 8765)
            vector_store: Optional vector store for semantic search
            pack_builder: Optional pack builder for export
            workspace_path: Path to the workspace root
        """
        self.blocks = blocks
        self.port = port
        self.vector_store = vector_store
        self.pack_builder = pack_builder
        self.workspace_path = workspace_path
        self.connection_manager = ConnectionManager()
        self._shutdown_event = asyncio.Event()

        # Create FastAPI app
        self.app = FastAPI(
            title="SpecMem UI",
            description="Web interface for SpecMem agent memory",
            version="0.1.0",
        )

        self._setup_middleware()
        self._setup_routes()
        self._setup_static_files()

    def _setup_middleware(self):
        """Configure CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for local dev
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Set up API routes."""
        # Set context for API endpoints
        api.set_context(
            blocks=self.blocks,
            vector_store=self.vector_store,
            pack_builder=self.pack_builder,
            workspace_path=self.workspace_path,
        )

        # Include API router
        self.app.include_router(api.router)

        # Set up context API if memory bank is available
        self._setup_context_api()

        # WebSocket endpoint for live updates and context queries
        @self.app.websocket("/api/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.connection_manager.connect(websocket)
            try:
                # Send initial connected message
                await websocket.send_json(
                    {
                        "type": "connected",
                        "message": "Connected to SpecMem live updates",
                    }
                )

                # Keep connection alive and listen for messages
                while True:
                    try:
                        data = await asyncio.wait_for(
                            websocket.receive_text(),
                            timeout=30.0,
                        )
                        # Handle ping/pong for keepalive
                        if data == "ping":
                            await websocket.send_json({"type": "pong"})
                        else:
                            # Try to parse as JSON for context queries
                            await self._handle_ws_message(websocket, data)
                    except TimeoutError:
                        # Send keepalive ping
                        await websocket.send_json({"type": "ping"})
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)

    async def _handle_ws_message(self, websocket: WebSocket, data: str):
        """Handle WebSocket messages including context queries."""
        import json

        try:
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "query":
                await self._handle_context_query(websocket, message)
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    }
                )
        except json.JSONDecodeError:
            # Not JSON, ignore
            pass
        except Exception as e:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(e),
                }
            )

    async def _handle_context_query(self, websocket: WebSocket, message: dict):
        """Handle context query over WebSocket."""
        try:
            from specmem.context import endpoints as context_endpoints
            from specmem.context.optimizer import ContextChunk

            api = context_endpoints._context_api
            if api is None:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Context API not available",
                    }
                )
                return

            query = message.get("query", "")
            options = message.get("options", {})

            # Stream chunks
            async for item in api.stream_query(
                query=query,
                token_budget=options.get("token_budget"),
                format=options.get("format", "json"),
                type_filters=options.get("type_filters"),
                profile=options.get("profile"),
            ):
                if isinstance(item, ContextChunk):
                    await websocket.send_json(
                        {
                            "type": "chunk",
                            "data": item.to_dict(),
                        }
                    )
                else:  # StreamCompletion
                    await websocket.send_json(item.to_dict())

        except Exception as e:
            logger.error(f"Context query error: {e}")
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(e),
                }
            )

    def _setup_static_files(self):
        """Configure static file serving for frontend."""
        static_dir = Path(__file__).parent / "static"

        if static_dir.exists():
            self.app.mount(
                "/assets",
                StaticFiles(directory=static_dir / "assets"),
                name="assets",
            )

            @self.app.get("/")
            async def serve_index():
                index_path = static_dir / "index.html"
                if index_path.exists():
                    return FileResponse(index_path)
                return {"message": "SpecMem UI - Frontend not built"}
        else:

            @self.app.get("/")
            async def serve_placeholder():
                return {
                    "message": "SpecMem UI API",
                    "docs": "/docs",
                    "note": "Frontend not built. Run 'npm run build' in specmem/ui/frontend/",
                }

    def _setup_context_api(self):
        """Set up the Streaming Context API endpoints."""
        try:
            from specmem.context import ProfileManager, StreamingContextAPI
            from specmem.context import endpoints as context_endpoints
            from specmem.core.config import SpecMemConfig
            from specmem.core.memory_bank import MemoryBank
            from specmem.vectordb.embeddings import get_embedding_provider

            # Only set up if we have a vector store
            if self.vector_store is None:
                logger.debug("Vector store not available, skipping context API")
                return

            # Create memory bank
            try:
                config = SpecMemConfig.load()
                embedding_provider = get_embedding_provider(
                    provider=config.embedding.provider,
                    model=config.embedding.model,
                    api_key=config.embedding.get_api_key(),
                )
                memory_bank = MemoryBank(self.vector_store, embedding_provider)
            except Exception as e:
                logger.warning(f"Could not create memory bank: {e}")
                return

            # Create context API
            context_api = StreamingContextAPI(memory_bank)
            profile_manager = ProfileManager(self.workspace_path / ".specmem")

            # Set up endpoints
            context_endpoints.set_context_api(context_api)
            context_endpoints.set_profile_manager(profile_manager)

            # Include context router
            self.app.include_router(context_endpoints.router)

            logger.info("Streaming Context API enabled")

        except ImportError as e:
            logger.debug(f"Context API not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to set up context API: {e}")

    async def notify_refresh(self):
        """Notify all connected clients to refresh data."""
        await self.connection_manager.broadcast(
            {
                "type": "refresh",
                "message": "Data updated, please refresh",
            }
        )

    def update_blocks(self, blocks: list[SpecBlock]):
        """Update the blocks and notify clients."""
        self.blocks = blocks
        api.set_context(
            blocks=blocks,
            vector_store=self.vector_store,
            pack_builder=self.pack_builder,
            workspace_path=self.workspace_path,
        )

    def start(self):
        """Start the web server (blocking)."""
        import uvicorn

        # Check port availability
        if not is_port_available(self.port):
            try:
                self.port = find_available_port(self.port)
                console.print(f"[yellow]Port {self.port - 1} in use, using {self.port}[/yellow]")
            except RuntimeError as e:
                console.print(f"[red]Error: {e}[/red]")
                return

        console.print("\n[bold green]🚀 SpecMem UI starting...[/bold green]")
        console.print(f"[blue]   Local:   http://127.0.0.1:{self.port}[/blue]")
        console.print(f"[blue]   API:     http://127.0.0.1:{self.port}/api[/blue]")
        console.print(f"[blue]   Docs:    http://127.0.0.1:{self.port}/docs[/blue]")
        console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")

        uvicorn.run(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )

    async def start_async(self):
        """Start the web server asynchronously."""
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        await server.serve()

    def stop(self):
        """Signal the server to stop."""
        self._shutdown_event.set()
