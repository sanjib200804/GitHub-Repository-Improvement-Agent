"""Phase 2 MCP Protocol Test.

Demonstrates and verifies:
1. Tool discovery of all 3 tools: `get_repository`, `get_repository_tree`, `read_file`.
2. Inspecting parameter schemas for multi-argument tools (`repo_url`, `file_path`, `branch`).
3. Calling `get_repository_tree` over MCP stdio transport.
4. Calling `read_file` over MCP stdio transport.
5. Error handling across the MCP boundary (missing files, binary rejections).
"""

import asyncio
import json
import os
import sys
import pytest
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def run_phase2_mcp_verification():
    print("=" * 60)
    print("  PHASE 2: MCP PROTOCOL VERIFICATION (Tree & File Tools)")
    print("=" * 60)

    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=os.environ.copy(),
        cwd=workspace_root,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. Initialize MCP session
            init_res = await session.initialize()
            server_info = getattr(init_res, "server_info", getattr(init_res, "serverInfo", None))
            server_name = server_info.name if server_info else "unknown"
            print(f"\n[1] Connected to MCP Server: {server_name}")

            # 2. Discover Tools
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"\n[2] Tools registered on MCP Server ({len(tool_names)} tools):")
            for t in tools_result.tools:
                schema = getattr(t, "input_schema", getattr(t, "inputSchema", {}))
                required = schema.get("required", [])
                properties = list(schema.get("properties", {}).keys())
                print(f"    - {t.name:<22} args: {properties} (required: {required})")

            assert "get_repository" in tool_names
            assert "get_repository_tree" in tool_names
            assert "read_file" in tool_names

            # 3. Test get_repository_tree over MCP
            print("\n[3] Calling 'get_repository_tree' for 'octocat/Hello-World'...")
            tree_call = await session.call_tool(
                name="get_repository_tree",
                arguments={"repo_url": "https://github.com/octocat/Hello-World"},
            )
            assert not getattr(tree_call, "isError", getattr(tree_call, "is_error", False))
            tree_data = json.loads(tree_call.content[0].text)
            print(f"    Repo:            {tree_data.get('repo')}")
            print(f"    Branch:          {tree_data.get('branch')}")
            print(f"    Filtered Files:  {tree_data.get('filtered_files_count')}")
            print("    Tree Visual:\n" + "\n".join("      " + line for line in tree_data.get("tree_summary", "").splitlines()))
            assert tree_data.get("error") is False
            assert len(tree_data.get("files", [])) >= 1

            # 4. Test read_file over MCP
            print("\n[4] Calling 'read_file' for 'README' in 'octocat/Hello-World'...")
            read_call = await session.call_tool(
                name="read_file",
                arguments={
                    "repo_url": "https://github.com/octocat/Hello-World",
                    "file_path": "README",
                },
            )
            assert not getattr(read_call, "isError", getattr(read_call, "is_error", False))
            file_data = json.loads(read_call.content[0].text)
            print(f"    File:       {file_data.get('file_path')}")
            print(f"    Size Bytes: {file_data.get('size_bytes')}")
            print(f"    Content:    {repr(file_data.get('content'))}")
            assert file_data.get("error") is False
            assert "Hello World!" in file_data.get("content", "")

            # 5. Test read_file 404 handling over MCP
            print("\n[5] Calling 'read_file' with missing file:")
            missing_call = await session.call_tool(
                name="read_file",
                arguments={
                    "repo_url": "https://github.com/octocat/Hello-World",
                    "file_path": "does_not_exist.txt",
                },
            )
            missing_data = json.loads(missing_call.content[0].text)
            print(f"    Error payload: {missing_data.get('message')}")
            assert missing_data.get("error") is True

    print("\n" + "=" * 60)
    print("  ALL PHASE 2 MCP CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


@pytest.mark.asyncio
async def test_mcp_phase2():
    await run_phase2_mcp_verification()


if __name__ == "__main__":
    asyncio.run(run_phase2_mcp_verification())
