"""MCP filesystem server implementation."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class FilesystemServer:
    """A simple MCP server for filesystem operations."""
    
    def __init__(self, base_dir: str = "."):
        """Initialize the filesystem server.
        
        Args:
            base_dir: Base directory for file operations (defaults to current directory)
        """
        self.base_dir = Path(base_dir).resolve()
        self.request_id = 0
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the list of available tools."""
        return [
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "list_directory",
                "description": "List contents of a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the directory to list (defaults to base directory)"
                        }
                    },
                    "required": []
                }
            }
        ]
    
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
        
        try:
            if name == "read_file":
                return self._read_file(arguments["path"])
            elif name == "write_file":
                return self._write_file(arguments["path"], arguments["content"])
            elif name == "list_directory":
                path = arguments.get("path", ".")
                return self._list_directory(path)
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
    
    def _read_file(self, path: str) -> Dict[str, Any]:
        """Read a file and return its contents."""
        file_path = self._resolve_path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        content = file_path.read_text(encoding='utf-8')
        return {
            "content": [{
                "type": "text",
                "text": f"Contents of {path}:\n{content}"
            }]
        }
    
    def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file."""
        file_path = self._resolve_path(path)
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content, encoding='utf-8')
        return {
            "content": [{
                "type": "text",
                "text": f"Successfully wrote to {path}"
            }]
        }
    
    def _list_directory(self, path: str) -> Dict[str, Any]:
        """List the contents of a directory."""
        dir_path = self._resolve_path(path)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not dir_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        items = []
        for item in sorted(dir_path.iterdir()):
            item_type = "directory" if item.is_dir() else "file"
            items.append(f"{item.name} ({item_type})")
        
        items_text = "\n".join(items) if items else "(empty directory)"
        return {
            "content": [{
                "type": "text",
                "text": f"Contents of {path}:\n{items_text}"
            }]
        }
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the base directory."""
        resolved = (self.base_dir / path).resolve()
        
        # Ensure the path is within the base directory (security check)
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise ValueError(f"Path outside base directory: {path}")
        
        return resolved
    
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
                        "name": "filesystem-server",
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
    """Main entry point for the filesystem server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Filesystem Server")
    parser.add_argument("--base-dir", default=".", help="Base directory for operations")
    args = parser.parse_args()
    
    server = FilesystemServer(args.base_dir)
    
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
