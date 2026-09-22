"""MCP Client integration with LangChain.

This module bridges the Model Context Protocol (MCP) server with LangChain:
1. Spawns and communicates with the MCP server subprocess via `stdio_client`.
2. Handles the JSON-RPC initialization handshake.
3. Automatically converts MCP tool definitions into LangChain `BaseTool` instances
   using `langchain_mcp_adapters.tools.load_mcp_tools`.
"""

import os
import sys
from contextlib import asynccontextmanager, AsyncExitStack
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools

load_dotenv()


def get_server_parameters(
    server_name: str = "github",
    workspace_dir: Optional[str] = None,
) -> StdioServerParameters:
    """Build the stdio connection parameters to launch a specific MCP server (github or linkedin)."""
    if not workspace_dir:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_dir = os.path.dirname(current_dir)

    module_map = {
        "github": "mcp_servers.github.server",
        "linkedin": "mcp_servers.linkedin.server",
    }
    target_module = module_map.get(server_name.lower(), "mcp_server.server")

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", target_module],
        env=os.environ.copy(),
        cwd=workspace_dir,
    )


def get_default_server_parameters(workspace_dir: Optional[str] = None) -> StdioServerParameters:
    """Build the stdio connection parameters to launch the default GitHub MCP server."""
    return get_server_parameters("github", workspace_dir=workspace_dir)


@asynccontextmanager
async def mcp_session_scope(
    server_params: Optional[StdioServerParameters] = None,
) -> AsyncGenerator[Tuple[ClientSession, List[BaseTool]], None]:
    """Async context manager that establishes a single MCP session and loads LangChain tools."""
    if server_params is None:
        server_params = get_default_server_parameters()

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            yield session, tools


@asynccontextmanager
async def multi_mcp_session_scope(
    server_names: Optional[List[str]] = None,
) -> AsyncGenerator[Tuple[Dict[str, ClientSession], List[BaseTool]], None]:
    """Async context manager that connects to multiple MCP servers concurrently and aggregates tools.

    Spawns both GitHub and LinkedIn MCP servers, initializes standard JSON-RPC sessions,
    and aggregates all exposed tools into a unified LangChain tool list.

    Yields:
        (sessions_dict, all_tools): Dict of server names to sessions, and combined BaseTools.
    """
    names = server_names or ["github", "linkedin"]
    sessions: Dict[str, ClientSession] = {}
    all_tools: List[BaseTool] = []

    async with AsyncExitStack() as stack:
        for name in names:
            params = get_server_parameters(name)
            read_stream, write_stream = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            tools = await load_mcp_tools(session)
            sessions[name] = session
            all_tools.extend(tools)

        yield sessions, all_tools

