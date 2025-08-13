"""Simple MCP (Model Context Protocol) client implementation."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional


class MCPClient:
    """A simple MCP client for connecting to MCP servers."""
    
    def __init__(self, server_command: List[str]):
        """Initialize the MCP client.
        
        Args:
            server_command: Command and arguments to start the MCP server
        """
        self.server_command = server_command
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self.logger = logging.getLogger(__name__)
    
    async def start(self) -> None:
        """Start the MCP server process."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.logger.info(f"Started MCP server: {' '.join(self.server_command)}")
        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.logger.info("Stopped MCP server")
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request to the MCP server.
        
        Args:
            method: The method name to call
            params: Optional parameters for the method
            
        Returns:
            The response from the server
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not started")
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        
        if params:
            request["params"] = params
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
        
        response = json.loads(response_line.decode().strip())
        
        if "error" in response:
            raise RuntimeError(f"MCP server error: {response['error']}")
        
        return response.get("result", {})
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP connection."""
        return await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "genai-workflow-starter",
                "version": "1.0.0"
            }
        })
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server."""
        result = await self.send_request("tools/list")
        return result.get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the server.
        
        Args:
            name: The tool name to call
            arguments: Arguments to pass to the tool
            
        Returns:
            The tool result
        """
        params = {"name": name}
        if arguments:
            params["arguments"] = arguments
            
        return await self.send_request("tools/call", params)


async def main():
    """Example usage of the MCP client."""
    logging.basicConfig(level=logging.INFO)
    
    # Example: Connect to a filesystem server
    client = MCPClient(["python", "-m", "mcp.servers.filesystem", "--base-dir", "."])
    
    try:
        await client.start()
        await client.initialize()
        
        # List available tools
        tools = await client.list_tools()
        print("Available tools:", [tool["name"] for tool in tools])
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
