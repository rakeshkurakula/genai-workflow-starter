# genai-workflow-starter

A GenAI workflow starter with comprehensive tooling and infrastructure.

## Features

### MCP Integration

This project includes Model Context Protocol (MCP) integration with:

- **MCP Client** (`apps/api/mcp/client.py`): Simple MCP client for connecting to MCP servers
- **Filesystem Server** (`apps/api/mcp/servers/filesystem/`): MCP server for file operations (read, write, list directories)
- **Web Server** (`apps/api/mcp/servers/web/`): MCP server for web operations (HTTP requests, API calls)

#### Usage Examples

##### Running the Filesystem Server
```bash
cd apps/api
python -m mcp.servers.filesystem --base-dir ./
```

##### Running the Web Server
```bash
cd apps/api
python -m mcp.servers.web
```

##### Using the MCP Client
```python
from mcp.client import MCPClient

# Connect to filesystem server
client = MCPClient(["python", "-m", "mcp.servers.filesystem", "--base-dir", "."])
await client.start()
await client.initialize()

# List available tools
tools = await client.list_tools()
print([tool["name"] for tool in tools])

# Call a tool
result = await client.call_tool("read_file", {"path": "README.md"})
print(result)

await client.stop()
```

#### Available Tools

**Filesystem Server:**
- `read_file`: Read contents of a file
- `write_file`: Write content to a file  
- `list_directory`: List contents of a directory

**Web Server:**
- `fetch_url`: Fetch content from a URL (GET/POST/etc.)
- `post_data`: Send POST request with JSON data

Both servers implement the MCP protocol v2024-11-05 and can be used with any MCP-compatible client.
