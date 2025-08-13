# Quick Start Guide

## Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rakeshkurakula/genai-workflow-starter.git
   cd genai-workflow-starter
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up the API environment:
   ```bash
   cd apps/api
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Running the Application

### Development Mode

1. Start all services:
   ```bash
   npm run dev
   ```

2. The API will be available at: http://localhost:8000
   The web app will be available at: http://localhost:3000

### API Only

```bash
cd apps/api
uvicorn main:app --reload
```

## Basic Usage

### Chat Agent

```python
from agents.chat_agent import ChatAgent

agent = ChatAgent()
response = agent.invoke({"question": "Hello, how are you?"})
print(response)
```

### RAG Agent

```python
from agents.rag_agent import RAGAgent

rag_agent = RAGAgent()
response = rag_agent.invoke({"question": "What is this project about?"})
print(response)
```

## Next Steps

- Check out the [Architecture Guide](./ARCHITECTURE.md) to understand the system design
- Read [Extending the System](./EXTENDING.md) to add new agents
- Review [Design Decisions](./DECISIONS.md) for context on implementation choices

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port in the respective configuration files
2. **Python dependencies**: Ensure you're using the correct Python version
3. **Environment variables**: Make sure all required variables are set in `.env`

For more help, check the project issues on GitHub.
