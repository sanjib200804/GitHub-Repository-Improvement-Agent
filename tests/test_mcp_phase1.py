"""Phase 1 MCP Protocol Test.

Demonstrates and verifies:
1. Spawning the MCP server as a subprocess.
2. Initializing the MCP session over stdio (JSON-RPC 2.0 handshake).
3. Tool discovery via `tools/list`.
4. Inspecting the JSON Schema generated for `get_repository`.
5. Executing `get_repository` via `tools/call`.
6. Handling invalid arguments and API errors gracefully over MCP.
"""

import asyncio
import json
import os
import sys
import pytest
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def run_phase1_mcp_verification():
    print("=" * 60)
    print("  PHASE 1: MCP PROTOCOL VERIFICATION")
    print("=" * 60)

    # 1. Configure the MCP subprocess parameters
    # The MCP client spawns the server as a separate process and connects
    # to its standard input (stdin) and standard output (stdout).
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=os.environ.copy(),
        cwd=workspace_root,
    )

    print(f"\n[1] Spawning MCP server subprocess:")
    print(f"    Command: {server_params.command} {' '.join(server_params.args)}")
    print(f"    CWD:     {server_params.cwd}")

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 2. Protocol Handshake: Initialize
            init_result = await session.initialize()
            server_info = getattr(init_result, "server_info", getattr(init_result, "serverInfo", None))
            server_name = server_info.name if server_info else "unknown"
            protocol_ver = getattr(init_result, "protocol_version", getattr(init_result, "protocolVersion", "unknown"))

            print("\n[2] MCP Session Initialized:")
            print(f"    Server Name:    {server_name}")
            print(f"    Protocol Ver:   {protocol_ver}")

            # 3. Tool Discovery: tools/list
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print("\n[3] Discovered Tools from MCP Server:")
            for t in tools_result.tools:
                schema = getattr(t, "input_schema", getattr(t, "inputSchema", {}))
                print(f"    - Name:        {t.name}")
                print(f"      Description: {t.description.strip().splitlines()[0] if t.description else ''}")
                print(f"      Schema:      {json.dumps(schema)}")

            assert "get_repository" in tool_names, "Expected 'get_repository' tool to be exposed"

            # 4. Tool Execution: tools/call
            # Sends JSON-RPC method: "tools/call" with params: {"name": "get_repository", "arguments": {...}}
            print("\n[4] Calling tool 'get_repository' for 'octocat/Hello-World':")
            call_result = await session.call_tool(
                name="get_repository",
                arguments={"repo_url": "https://github.com/octocat/Hello-World"},
            )

            # FastMCP returns output in content items (usually TextContent containing JSON string)
            is_err = getattr(call_result, "isError", getattr(call_result, "is_error", False))
            assert not is_err, "Expected tool call to succeed without error"
            raw_text = call_result.content[0].text
            repo_data = json.loads(raw_text)

            print("\n[5] Tool Call Result (Structured JSON-RPC Payload received):")
            print(json.dumps(repo_data, indent=2))

            # Validate returned fields
            assert repo_data.get("name") == "Hello-World"
            assert repo_data.get("owner") == "octocat"
            assert repo_data.get("default_branch") == "master"
            assert "stars" in repo_data
            assert "forks" in repo_data

            # 6. Test Error Handling over MCP (Nonexistent repo)
            print("\n[6] Calling tool 'get_repository' with nonexistent repo:")
            err_call = await session.call_tool(
                name="get_repository",
                arguments={"repo_url": "octocat/nonexistent-repository-xyz-999"},
            )
            err_data = json.loads(err_call.content[0].text)
            print(f"    Returned error message: {err_data.get('message')}")
            assert err_data.get("error") is True

    print("\n" + "=" * 60)
    print("  ALL PHASE 1 MCP CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


@pytest.mark.asyncio
async def test_mcp_phase1():
    await run_phase1_mcp_verification()


if __name__ == "__main__":
    asyncio.run(run_phase1_mcp_verification())
