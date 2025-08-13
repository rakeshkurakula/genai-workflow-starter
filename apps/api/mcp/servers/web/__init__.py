"""MCP web server implementation."""

import asyncio
import json
import sys
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:
    requests = None


class WebServer:
    """A simple MCP server for web operations."""
    
    def __init__(self, base_url: str = None):
        """Initialize the web server.
        
        Args:
            base_url: Base URL for relative requests (optional)
        """
        self.base_url = base_url
        if requests is None:
            print("Warning: requests library not available. Install with: pip install requests")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the list of available tools."""
        tools = [
            {
                "name": "fetch_url",
                "description": "Fetch content from a URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch"
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, etc.)",
                            "default": "GET"
                        }
                    },
                    "required": ["url"]
                }
            }
        ]
        
        if requests is not None:
            tools.append({
                "name": "post_data",
                "description": "Send POST request with data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to post to"
                        },
                        "data": {
                            "type": "object",
                            "description": "Data to send in POST request"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Additional headers to send"
                        }
                    },
                    "required": ["url", "data"]
                }
            })
        
        return tools
    
    def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool with the given arguments.
        
        Args:
            name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if arguments is None:
            arguments = {}
        
        if requests is None:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Error: requests library not installed"}]
            }
        
        try:
            if name == "fetch_url":
                return self._fetch_url(arguments["url"], arguments.get("method", "GET"))
            elif name == "post_data":
                return self._post_data(
                    arguments["url"], 
                    arguments["data"], 
                    arguments.get("headers", {})
                )
            else:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}]
                }
        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: {str(e)}"}]
            }
    
    def _fetch_url(self, url: str, method: str = "GET") -> Dict[str, Any]:
        """Fetch content from a URL."""
        # Resolve URL if base_url is provided
        if self.base_url and not urlparse(url).netloc:
            url = urljoin(self.base_url, url)
        
        # Basic URL validation
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Unsupported scheme: {parsed.scheme}")
        
        try:
            response = requests.request(method, url, timeout=10)
            response.raise_for_status()
            
            # Try to get text content, fall back to raw if not possible
            try:
                content = response.text
            except UnicodeDecodeError:
                content = f"Binary content ({len(response.content)} bytes)"
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"Response from {url} (Status: {response.status_code}):\n\n{content[:2000]}{'...' if len(content) > 2000 else ''}"
                }]
            }
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def _post_data(self, url: str, data: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Send POST request with data."""
        # Resolve URL if base_url is provided
        if self.base_url and not urlparse(url).netloc:
            url = urljoin(self.base_url, url)
        
        # Basic URL validation
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Unsupported scheme: {parsed.scheme}")
        
        if headers is None:
            headers = {}
        
        # Set default content type if not specified
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        try:
            if headers.get('Content-Type') == 'application/json':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                response = requests.post(url, data=data, headers=headers, timeout=10)
                
            response.raise_for_status()
            
            try:
                content = response.text
            except UnicodeDecodeError:
                content = f"Binary response ({len(response.content)} bytes)"
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"POST to {url} successful (Status: {response.status_code}):\n\n{content[:1000]}{'...' if len(content) > 1000 else ''}"
                }]
            }
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"POST request failed: {str(e)}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "web-server",
                        "version": "1.0.0"
                    }
                }
            elif method == "tools/list":
                result = {"tools": self.get_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = self.call_tool(tool_name, tool_args)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }


async def main():
    """Main entry point for the web server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Web Server")
    parser.add_argument("--base-url", help="Base URL for relative requests")
    args = parser.parse_args()
    
    server = WebServer(args.base_url)
    
    # Read requests from stdin and write responses to stdout
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            if not line:
                break
                
            request = json.loads(line.strip())
            response = await server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
