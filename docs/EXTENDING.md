# Extending the Workflow

This guide explains how to extend the GenAI Workflow Starter by adding new tools and agent nodes.

## Adding a New Tool

Tools are located in `apps/api/tools/` and follow a consistent pattern. Use `web_search.py` and `code_exec_py.py` as reference implementations.

### 1. Create the Tool Module

Create a new Python file in `apps/api/tools/your_tool.py`:

```python
from typing import Dict, Any
from pydantic import BaseModel, Field
from .base import BaseTool

class YourToolInput(BaseModel):
    """Input schema for your tool"""
    query: str = Field(..., description="Description of the input parameter")
    # Add more parameters as needed

class YourTool(BaseTool):
    """Your tool description"""
    
    name = "your_tool"
    description = "Brief description of what your tool does"
    
    def __init__(self):
        super().__init__()
        # Initialize any required clients or configuration
    
    async def _execute(self, input_data: YourToolInput) -> Dict[str, Any]:
        """Execute the tool with the given input"""
        try:
            # Implement your tool logic here
            result = await self._do_work(input_data.query)
            
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "tool": self.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "tool": self.name
                }
            }
    
    async def _do_work(self, query: str) -> str:
        """Implement your core tool functionality"""
        # Add your implementation here
        pass
```

### 2. Add JSON Schema Definition

Each tool needs a JSON schema for the agent to understand how to use it. Add this to your tool class:

```python
@property
def schema(self) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Description of the query parameter"
                    }
                },
                "required": ["query"]
            }
        }
    }
```

### 3. Add Input Validation and Guardrails

Implement appropriate validation and safety measures:

```python
def validate_input(self, input_data: YourToolInput) -> bool:
    """Validate input before execution"""
    if not input_data.query or len(input_data.query) > 1000:
        raise ValueError("Query must be between 1 and 1000 characters")
    return True

async def _execute_with_timeout(self, input_data: YourToolInput, timeout: int = 30) -> Dict[str, Any]:
    """Execute with timeout protection"""
    import asyncio
    try:
        return await asyncio.wait_for(self._execute(input_data), timeout=timeout)
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Tool execution timed out after {timeout} seconds"
        }
```

### 4. Register the Tool

Add your tool to the tool registry in `apps/api/tools/__init__.py`:

```python
from .your_tool import YourTool

# Add to the AVAILABLE_TOOLS dictionary
AVAILABLE_TOOLS = {
    "web_search": WebSearchTool,
    "code_exec_py": PythonCodeTool,
    "your_tool": YourTool,  # Add this line
}
```

### 5. Add Tests

Create `apps/api/tests/test_your_tool.py`:

```python
import pytest
from apps.api.tools.your_tool import YourTool, YourToolInput

@pytest.fixture
def tool():
    return YourTool()

@pytest.mark.asyncio
async def test_your_tool_success(tool):
    """Test successful tool execution"""
    input_data = YourToolInput(query="test query")
    result = await tool._execute(input_data)
    
    assert result["success"] is True
    assert "result" in result
    assert result["metadata"]["tool"] == "your_tool"

@pytest.mark.asyncio
async def test_your_tool_validation(tool):
    """Test input validation"""
    with pytest.raises(ValueError):
        input_data = YourToolInput(query="")
        tool.validate_input(input_data)
```

## Adding a New Agent Node

Agent nodes are located in `agents/` and implement specific reasoning patterns.

### 1. Create the Node Class

Create `agents/your_node.py`:

```python
from typing import Dict, Any, List
from .base import BaseNode
from apps.api.tools import get_tool

class YourNode(BaseNode):
    """Node that does specific reasoning or processing"""
    
    def __init__(self, tools: List[str] = None):
        super().__init__()
        self.available_tools = tools or []
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and return updated state"""
        try:
            # Extract relevant information from state
            user_query = state.get("user_query", "")
            context = state.get("context", {})
            
            # Implement your node logic
            result = await self._process_logic(user_query, context)
            
            # Update state with results
            return {
                **state,
                "your_node_result": result,
                "processed_by": self.__class__.__name__
            }
        except Exception as e:
            return {
                **state,
                "error": f"Node processing failed: {str(e)}"
            }
    
    async def _process_logic(self, query: str, context: Dict[str, Any]) -> Any:
        """Implement your specific processing logic"""
        # Add your implementation here
        pass
```

### 2. Add to Agent Graph

Integrate your node into the agent graph in `agents/graph.py`:

```python
from .your_node import YourNode

# Add to the graph construction
def create_agent_graph():
    graph = StateGraph(AgentState)
    
    # Add existing nodes...
    graph.add_node("router", router_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("your_node", YourNode())  # Add your node
    
    # Add edges
    graph.add_edge("router", "your_node")  # Define routing logic
    graph.add_edge("your_node", "answerer")
    
    return graph.compile()
```

### 3. Update Routing Logic

Modify the router to direct appropriate queries to your node:

```python
# In agents/router.py
async def should_use_your_node(query: str) -> bool:
    """Determine if query should be routed to your node"""
    keywords = ["specific", "keywords", "for", "your", "node"]
    return any(keyword in query.lower() for keyword in keywords)
```

## Testing Your Extensions

### Run Tool Tests
```bash
# Test specific tool
pytest apps/api/tests/test_your_tool.py -v

# Test all tools
pytest apps/api/tests/ -v
```

### Test Agent Integration
```bash
# Start the API server
uv run fastapi dev apps/api/main.py

# Test via API
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "test query for your tool"}'
```

### Test Web Interface
```bash
# Start the web app
pnpm dev

# Navigate to http://localhost:3000 and test your extensions
```

## Best Practices

### Tool Development
- **Timeouts**: Always implement timeouts for external API calls
- **Error Handling**: Provide clear error messages and handle edge cases
- **Validation**: Validate all inputs thoroughly
- **Logging**: Use structured logging for debugging
- **Documentation**: Document parameters and expected behavior

### Agent Node Development  
- **State Management**: Preserve important state information
- **Idempotency**: Ensure nodes can be safely re-executed
- **Composability**: Design nodes to work well with others
- **Testing**: Test both success and failure scenarios

### Code Organization
- Follow the established patterns in existing tools/nodes
- Keep tool logic separate from agent logic
- Use type hints consistently
- Write comprehensive tests
- Update documentation when adding features

## Troubleshooting

### Common Issues
1. **Tool not found**: Ensure tool is registered in `__init__.py`
2. **Schema errors**: Validate JSON schema format
3. **Import errors**: Check Python path and dependencies
4. **Agent routing**: Verify routing logic in router node

### Debugging Tips
- Use `uv run fastapi dev` for hot reload during development
- Check API logs at `/api/health` endpoint
- Test tools independently before integrating
- Use the web interface for end-to-end testing
