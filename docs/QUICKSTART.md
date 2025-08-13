# GenAI Workflow Starter - Quick Start Guide

## Mental Model: Your GenAI Development Journey

### 🧠 Think of This Repo As Your GenAI Swiss Army Knife

This isn't just another template—it's a **production-ready GenAI platform** that handles the hard stuff so you can focus on building amazing AI experiences.

**The Big Picture:**
- 🏗️ **Foundation Layer**: Robust infrastructure (Docker, monitoring, auth)
- 🤖 **Agent Layer**: Pre-built intelligent agents with memory and tools
- 🔌 **Integration Layer**: MCP servers for seamless tool connectivity
- 🚀 **API Layer**: FastAPI backend with async processing
- 🎨 **Frontend Layer**: Modern React/Next.js interface

### 🎯 What You Get Out of the Box

✅ **Production Infrastructure**
- Docker containerization
- Environment management
- Monitoring and logging
- Security best practices

✅ **Intelligent Agent System**
- Chat agents with memory
- RAG (Retrieval-Augmented Generation) agents
- Agent orchestration and routing
- Custom tool integration

✅ **Data Pipeline**
- Document ingestion
- Hybrid search (BM25 + FAISS)
- Vector embeddings
- Knowledge base management

✅ **Developer Experience**
- TypeScript SDK
- API documentation
- Development workflows
- Testing framework

---

## 🚀 Plug-and-Play Checklist

### Phase 1: Environment Setup (5 minutes)

**Prerequisites Check:**
- [ ] Python 3.8+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Docker installed and running (`docker --version`)
- [ ] Git installed (`git --version`)

**Quick Setup:**
```bash
# 1. Clone and enter
git clone https://github.com/rakeshkurakula/genai-workflow-starter.git
cd genai-workflow-starter

# 2. One-command setup
make setup
# OR manually:
npm install && cd apps/api && pip install -r requirements.txt
```

### Phase 2: Configuration (3 minutes)

**Environment Variables:**
```bash
# Copy example configs
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env

# Edit with your keys (minimum required):
# - OPENAI_API_KEY=your_openai_key
# - DATABASE_URL=sqlite:///./genai.db
```

**Quick Test:**
```bash
# Verify setup
make health-check
```

### Phase 3: Launch & Verify (2 minutes)

**Start Everything:**
```bash
# Development mode (all services)
make dev

# OR individual services:
# make api      # Just the API
# make web      # Just the frontend
# make agents   # Just the agent system
```

**Verify It's Working:**
- [ ] API Health: http://localhost:8000/health
- [ ] API Docs: http://localhost:8000/docs
- [ ] Web App: http://localhost:3000
- [ ] Agent Status: http://localhost:8000/agents/status

### Phase 4: First AI Interaction (1 minute)

**Test the Chat Agent:**
```python
# Quick Python test
from agents.chat_agent import ChatAgent

agent = ChatAgent()
response = agent.invoke({"question": "Hello! Explain what this system can do."})
print(response)
```

**Test via API:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What can you help me with?"}'
```

**Test via Web UI:**
- Navigate to http://localhost:3000
- Click "Try Chat Agent"
- Send a test message

---

## 🛠️ Common Customization Patterns

### Add Your Own Agent (5 minutes)

1. **Create agent file:**
```python
# agents/my_agent.py
from .base_agent import BaseAgent

class MyAgent(BaseAgent):
    def invoke(self, input_data):
        # Your custom logic here
        return {"response": "Custom agent response"}
```

2. **Register in graph:**
```python
# agents/graph.py
from .my_agent import MyAgent

# Add to agent_graph definition
```

### Connect External APIs (3 minutes)

1. **Add MCP server:**
```bash
# Create new MCP server
mkdir apps/api/mcp/servers/my_service
# Follow existing patterns in filesystem/ or web/
```

2. **Register tools:**
```python
# agents/tools/my_tools.py
def my_custom_tool(query: str):
    # Your external API integration
    return result
```

### Add New Data Sources (2 minutes)

```python
# Ingest new documents
from apps.api.ingest import DocumentIngester

ingester = DocumentIngester()
ingester.add_documents([
    {"content": "Your content", "metadata": {"source": "custom"}}
])
```

---

## 🔧 Development Workflows

### Daily Development
```bash
# Start your day
make dev

# Run tests
make test

# Check code quality
make lint

# Clean restart
make clean && make setup && make dev
```

### Adding Features
```bash
# Create feature branch
git checkout -b feature/my-feature

# Develop with hot reload
make dev

# Test your changes
make test-feature

# Ready to commit
make pre-commit
```

### Production Deployment
```bash
# Build for production
make build

# Deploy (configure your target first)
make deploy

# Health check production
make prod-health
```

---

## 🎯 Common Use Cases & Quick Wins

### 1. Document Q&A System (15 minutes)
```bash
# 1. Add your documents
cp your-docs/* data/seed/documents/

# 2. Ingest them
make ingest

# 3. Query via RAG agent
curl -X POST "http://localhost:8000/rag" \
  -d '{"question": "What does my document say about X?"}'
```

### 2. Custom Chatbot (10 minutes)
```python
# Customize the chat agent personality
# Edit agents/chat_agent.py system prompt
SYSTEM_PROMPT = "You are a helpful assistant specialized in [your domain]..."
```

### 3. API Integration Bot (20 minutes)
```python
# Create a new MCP server for your API
# Follow the pattern in mcp/servers/web/
# Add authentication, rate limiting, etc.
```

### 4. Multi-Agent Workflow (30 minutes)
```python
# Chain multiple agents
result1 = research_agent.invoke({"topic": "AI trends"})
result2 = analysis_agent.invoke({"data": result1})
final = summary_agent.invoke({"analysis": result2})
```

---

## 🚨 Troubleshooting

### Quick Fixes

**Port conflicts:**
```bash
# Kill processes on common ports
make kill-ports
# Or manually: lsof -ti:8000 | xargs kill -9
```

**Dependency issues:**
```bash
# Clean install
make clean-install
```

**Database issues:**
```bash
# Reset database
make db-reset
```

**Agent not responding:**
```bash
# Check agent health
curl http://localhost:8000/agents/health

# Restart agents only
make restart-agents
```

### Common Issues

❌ **"ModuleNotFoundError"**
→ Run `pip install -r requirements.txt` in the right directory

❌ **"Port already in use"**
→ Run `make kill-ports` or change ports in config

❌ **"API key not found"**
→ Check your `.env` file has the required keys

❌ **"Agents not starting"**
→ Verify Python path and dependencies: `make verify-setup`

---

## 🎓 Learning Path

### Week 1: Master the Basics
- [ ] Complete this quickstart
- [ ] Read [Architecture Guide](./ARCHITECTURE.md)
- [ ] Try all example agents
- [ ] Modify agent prompts

### Week 2: Customize & Extend
- [ ] Create your first custom agent
- [ ] Add a new data source
- [ ] Integrate an external API
- [ ] Read [Extending Guide](./EXTENDING.md)

### Week 3: Production Ready
- [ ] Set up monitoring
- [ ] Add authentication
- [ ] Deploy to staging
- [ ] Review [Design Decisions](./DECISIONS.md)

---

## 🤝 Next Steps

**Immediate Actions:**
1. 🏃‍♂️ Complete the Phase 1-4 checklist above
2. 📖 Read the [Architecture Guide](./ARCHITECTURE.md) to understand the system
3. 🔧 Try the "Common Use Cases" section for quick wins
4. 🌟 Star this repo if it helps you!

**Dive Deeper:**
- 🏗️ [Architecture Guide](./ARCHITECTURE.md) - System design and patterns
- 🔧 [Extending Guide](./EXTENDING.md) - Add agents, tools, and integrations
- 🎯 [Design Decisions](./DECISIONS.md) - Why we built it this way

**Get Help:**
- 🐛 [Create an Issue](https://github.com/rakeshkurakula/genai-workflow-starter/issues) for bugs
- 💡 [Start a Discussion](https://github.com/rakeshkurakula/genai-workflow-starter/discussions) for questions
- 📧 Contact the maintainer for enterprise support

---

*Remember: This is a living system. Start simple, then gradually add complexity as you understand each piece. The modular design means you can always swap out components later.*

**Happy building! 🚀**
