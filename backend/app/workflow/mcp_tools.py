import asyncio
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from contextlib import AsyncExitStack
from app.core.logging import logger

if TYPE_CHECKING:
    from mcp import ClientSession


class MCPClient:
    def __init__(
        self,
        server_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 5,
        sse_read_timeout: float = 300,
    ):
        self.server_url = server_url
        self.exit_stack = AsyncExitStack()
        self.headers = headers or {}
        self.timeout = timeout
        self.sse_read_timeout = sse_read_timeout
        self.session: Optional["ClientSession"] = None

    async def connect_to_sse_server(self) -> None:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        await self.cleanup()

        streams = await self.exit_stack.enter_async_context(
            sse_client(
                url=self.server_url,
                headers=self.headers,
                timeout=self.timeout,
                sse_read_timeout=self.sse_read_timeout,
            )
        )
        session = await self.exit_stack.enter_async_context(ClientSession(*streams))
        await session.initialize()
        self.session = session

    async def list_tools(self) -> List[Dict[str, Any]]:
        if not self.session:
            raise RuntimeError("Not connected to server")
        response = await self.session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

    async def call_tool(self, tool_name: str, tool_args: Dict) -> str:
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.call_tool(tool_name, tool_args)
        if hasattr(result, "content"):
            content = result.content
            if isinstance(content, list):
                return "".join(getattr(item, "text", str(item)) for item in content)
            return str(content)
        return str(result)

    async def cleanup(self):
        await self.exit_stack.aclose()
        self.exit_stack = AsyncExitStack()
        self.session = None

    async def __aenter__(self):
        await self.connect_to_sse_server()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()


async def mcp_tools(
    server_url: str,
    tool_name: str,
    tool_args: Dict,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5,
    sse_read_timeout: float = 300,
) -> str:
    async with MCPClient(server_url, headers, timeout, sse_read_timeout) as client:
        return await client.call_tool(tool_name, tool_args)


async def mcp_list_tools(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5,
    sse_read_timeout: float = 300,
) -> List[Dict[str, Any]]:
    try:
        async with MCPClient(url, headers, timeout, sse_read_timeout) as client:
            tools = await client.list_tools()
            return tools
    except Exception as e:
        logger.error(f"Failed to list MCP tools from {url}: {e}")
        return []


async def mcp_call_tools(
    url: str,
    tool_name: str,
    tool_args: Dict,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5,
    sse_read_timeout: float = 300,
) -> str:
    async with MCPClient(url, headers, timeout, sse_read_timeout) as client:
        result = await client.call_tool(tool_name, tool_args)
        return result
