# MaxOS

A multi-agent operating system powered by AI.

## Features

- **Multi-Agent System**: Coordinate multiple AI agents to work together
- **REST API**: Easy-to-use HTTP interface for all operations
- **gRPC API**: High-performance gRPC interface with streaming support
- **Command Line Interface**: Interactive CLI for direct agent interaction

### Multi-Interface Support

- **REST API**: HTTP/JSON interface on port 8080 (see [docs/API.md](docs/API.md))
- **gRPC API**: High-performance gRPC interface with streaming support on port 50051 (see [docs/GRPC_API.md](docs/GRPC_API.md))
- **CLI**: Interactive command-line interface for direct agent interaction

## LLM-Powered Intent Classification

MaxOS now features an intelligent intent classification system that uses Large Language Models (Claude or OpenAI) to understand user queries and automatically route them to the appropriate subsystem.

### How It Works

When you send a query to MaxOS, it analyzes the intent and determines whether to:
- Route to the **Multi-Agent System** for complex orchestration tasks
- Execute as a **Knowledge Query** for information retrieval
- Handle as a **System Command** for OS-level operations

### Configuration

Set up your LLM provider by configuring environment variables:

```bash
# For Claude (Anthropic)
export LLM_PROVIDER=claude
export ANTHROPIC_API_KEY=your_api_key_here

# For OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_api_key_here
```

### Example Classifications

**Multi-Agent Task:**
```
Query: "Research the latest AI trends and create a summary report"
→ Routes to Multi-Agent System
→ Spawns researcher + writer agents
```

**Knowledge Query:**
```
Query: "What is the capital of France?"
→ Routes to Knowledge System
→ Returns: "Paris"
```

**System Command:**
```
Query: "List all running agents"
→ Routes to System Commands
→ Executes: agent list
```

### Benefits

- **Natural Language Interface**: No need to learn command syntax
- **Intelligent Routing**: Automatic detection of query intent
- **Flexible Backend**: Support for multiple LLM providers
- **Extensible**: Easy to add new intent categories

## Quick Start

### Running the gRPC API

Start the gRPC server:
```bash
go run cmd/grpc-server/main.go
```

The server will start on port 50051 by default.

### Prerequisites

- Go 1.21 or higher
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/MaxTezza/MaxOS.git
cd MaxOS

# Install dependencies
go mod download

# Build the system
go build -o maxos cmd/main.go

# Run MaxOS
./maxos
```

### Using the REST API

Start the REST API server:
```bash
go run cmd/api-server/main.go
```

Example API request:
```bash
curl -X POST http://localhost:8080/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "assistant",
    "type": "general",
    "config": {
      "model": "gpt-4"
    }
  }'
```

### Using the CLI

Start the interactive CLI:
```bash
go run cmd/cli/main.go
```

Available commands:
- `agent create <name> <type>` - Create a new agent
- `agent list` - List all agents
- `agent delete <id>` - Delete an agent
- `task create <description>` - Create a new task
- `task list` - List all tasks
- `help` - Show all available commands

## Multi-Agent Orchestration System

MaxOS features a sophisticated multi-agent orchestration system that enables complex task execution through coordinated AI agents.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MaxOS Orchestrator                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Planner    │  │  Coordinator │  │   Monitor    │      │
│  │    Agent     │──│     Agent    │──│    Agent     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│  ┌─────────────────────────┼─────────────────────────────┐ │
│  │         Execution Layer │                             │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐        │ │
│  │  │ Research  │  │  Writer   │  │  Analyst  │  ...   │ │
│  │  │  Agent    │  │   Agent   │  │   Agent   │        │ │
│  │  └───────────┘  └───────────┘  └───────────┘        │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

1. **Hierarchical Agent Organization**
   - Planner agents for task decomposition
   - Coordinator agents for workflow management
   - Specialized worker agents for execution

2. **Dynamic Agent Spawning**
   - Agents can create sub-agents as needed
   - Automatic resource allocation
   - Agent lifecycle management

3. **Inter-Agent Communication**
   - Message passing between agents
   - Shared knowledge base
   - Event-driven coordination

4. **Task Decomposition**
   - Complex tasks broken into subtasks
   - Parallel execution where possible
   - Dependency management

### Example: Research Report Generation

```go
// User request: "Research quantum computing and write a report"

// 1. Planner Agent breaks down the task:
//    - Research quantum computing basics
//    - Research recent advances
//    - Research commercial applications
//    - Synthesize findings into report

// 2. Coordinator spawns specialized agents:
research1 := SpawnAgent("researcher", "quantum_basics")
research2 := SpawnAgent("researcher", "recent_advances")
research3 := SpawnAgent("researcher", "commercial_apps")

// 3. Agents execute in parallel:
results := coordinator.ExecuteParallel(research1, research2, research3)

// 4. Writer agent synthesizes results:
writer := SpawnAgent("writer", "technical_report")
report := writer.Synthesize(results)

// 5. Return completed report to user
```

### Agent Types

- **Planner**: Decomposes complex tasks
- **Researcher**: Gathers information from various sources
- **Analyst**: Processes and analyzes data
- **Writer**: Creates written content
- **Reviewer**: Quality checks and validation
- **Coordinator**: Manages multi-agent workflows

### Configuration

Configure the orchestration system in `config/orchestration.yaml`:

```yaml
orchestration:
  max_agents: 100
  max_depth: 5
  timeout: 300s
  parallel_execution: true
  
agent_types:
  planner:
    model: "gpt-4"
    temperature: 0.7
  researcher:
    model: "gpt-4"
    temperature: 0.5
  writer:
    model: "gpt-4"
    temperature: 0.8
```

## Development

### Project Structure

```
MaxOS/
├── cmd/
│   ├── main.go          # Main entry point
│   ├── api-server/      # REST API server
│   ├── grpc-server/     # gRPC API server
│   └── cli/             # CLI interface
├── internal/
│   ├── agents/          # Agent implementations
│   ├── orchestrator/    # Multi-agent orchestration
│   ├── api/             # API handlers
│   └── grpc/            # gRPC service implementations
├── pkg/
│   └── proto/           # Protocol buffer definitions
└── docs/
    ├── API.md           # REST API documentation
    └── GRPC_API.md      # gRPC API documentation
```

### Running Tests

```bash
go test ./...
```

### Building Docker Image

```bash
docker build -t maxos:latest .
docker run -p 8080:8080 -p 50051:50051 maxos:latest
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
