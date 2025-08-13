from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
from abc import ABC, abstractmethod


class NodeType(Enum):
    """Enum for different node types in the agent graph"""
    AGENT = "agent"
    TOOL = "tool"
    DECISION = "decision"
    END = "end"


@dataclass
class GraphNode:
    """Represents a node in the agent execution graph"""
    id: str
    type: NodeType
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] = None
    next_nodes: List[str] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.next_nodes is None:
            self.next_nodes = []


class BaseAgent(ABC):
    """Abstract base class for agents in the graph"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent with given input data"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for agent configuration"""
        pass


class ChatAgent(BaseAgent):
    """Agent for handling chat interactions"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Stub implementation
        message = input_data.get("message", "")
        return {
            "response": f"Chat agent processed: {message}",
            "type": "chat_response"
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model": {"type": "string", "default": "gpt-3.5-turbo"},
                "temperature": {"type": "number", "default": 0.7},
                "max_tokens": {"type": "integer", "default": 1000}
            }
        }


class RAGAgent(BaseAgent):
    """Agent for Retrieval Augmented Generation"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Stub implementation
        query = input_data.get("query", "")
        return {
            "response": f"RAG agent processed query: {query}",
            "retrieved_docs": [],
            "type": "rag_response"
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vector_db": {"type": "string", "default": "chroma"},
                "embedding_model": {"type": "string", "default": "text-embedding-ada-002"},
                "top_k": {"type": "integer", "default": 5}
            }
        }


class AgentGraph:
    """Manages the execution flow of agents in a graph structure"""
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.agents: Dict[str, BaseAgent] = {}
        self.start_node: Optional[str] = None
    
    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph"""
        self.nodes[node.id] = node
    
    def add_agent(self, agent: BaseAgent) -> None:
        """Add an agent to the graph"""
        self.agents[agent.agent_id] = agent
    
    def set_start_node(self, node_id: str) -> None:
        """Set the starting node for graph execution"""
        if node_id in self.nodes:
            self.start_node = node_id
        else:
            raise ValueError(f"Node {node_id} not found in graph")
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add an edge between two nodes"""
        if from_node in self.nodes and to_node in self.nodes:
            self.nodes[from_node].next_nodes.append(to_node)
        else:
            raise ValueError("One or both nodes not found in graph")
    
    async def execute(self, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the graph starting from the start node"""
        if not self.start_node:
            raise ValueError("No start node set for graph execution")
        
        current_node_id = self.start_node
        execution_result = initial_input.copy()
        execution_path = []
        
        while current_node_id:
            if current_node_id not in self.nodes:
                raise ValueError(f"Node {current_node_id} not found")
            
            node = self.nodes[current_node_id]
            execution_path.append(current_node_id)
            
            if node.type == NodeType.AGENT and current_node_id in self.agents:
                agent = self.agents[current_node_id]
                result = await agent.execute(execution_result)
                execution_result.update(result)
            elif node.type == NodeType.END:
                break
            
            # Simple next node selection (take first available)
            if node.next_nodes:
                current_node_id = node.next_nodes[0]
            else:
                break
        
        return {
            "result": execution_result,
            "execution_path": execution_path
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph to a dictionary"""
        return {
            "nodes": {
                node_id: {
                    "id": node.id,
                    "type": node.type.value,
                    "name": node.name,
                    "description": node.description,
                    "config": node.config,
                    "next_nodes": node.next_nodes
                }
                for node_id, node in self.nodes.items()
            },
            "start_node": self.start_node
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentGraph':
        """Create graph from dictionary representation"""
        graph = cls()
        
        for node_data in data.get("nodes", {}).values():
            node = GraphNode(
                id=node_data["id"],
                type=NodeType(node_data["type"]),
                name=node_data["name"],
                description=node_data.get("description"),
                config=node_data.get("config", {}),
                next_nodes=node_data.get("next_nodes", [])
            )
            graph.add_node(node)
        
        if data.get("start_node"):
            graph.set_start_node(data["start_node"])
        
        return graph


def create_default_graph() -> AgentGraph:
    """Create a default agent graph with basic chat and RAG capabilities"""
    graph = AgentGraph()
    
    # Create nodes
    chat_node = GraphNode(
        id="chat_agent",
        type=NodeType.AGENT,
        name="Chat Agent",
        description="Handles chat interactions",
        next_nodes=["end"]
    )
    
    rag_node = GraphNode(
        id="rag_agent",
        type=NodeType.AGENT,
        name="RAG Agent",
        description="Retrieval Augmented Generation",
        next_nodes=["end"]
    )
    
    end_node = GraphNode(
        id="end",
        type=NodeType.END,
        name="End",
        description="Terminal node"
    )
    
    # Add nodes to graph
    graph.add_node(chat_node)
    graph.add_node(rag_node)
    graph.add_node(end_node)
    
    # Create and add agents
    chat_agent = ChatAgent("chat_agent", {})
    rag_agent = RAGAgent("rag_agent", {})
    
    graph.add_agent(chat_agent)
    graph.add_agent(rag_agent)
    
    # Set default start node
    graph.set_start_node("chat_agent")
    
    return graph


if __name__ == "__main__":
    # Example usage
    graph = create_default_graph()
    print(json.dumps(graph.to_dict(), indent=2))
