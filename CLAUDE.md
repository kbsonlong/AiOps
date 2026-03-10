# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AIOps (AI for IT operations) project aimed at building intelligent monitoring agents. The current implementation is a **multi-source knowledge router** using LangChain and LangGraph, demonstrating a router pattern for multi-agent systems. The router classifies queries, routes them to specialized agents (GitHub, Notion, Slack), and synthesizes results.

The long-term vision (per README) includes:
- Automatic monitoring of system metrics (CPU, memory, disk, network)
- Anomaly detection and automated remediation
- Customizable monitoring and solution modules
- Multi-agent collaboration

## Development Environment

- **Python**: 3.12 (specified in `.python-version`)
- **Package manager**: `uv` (lock file `uv.lock`)
- **Dependencies**: Managed via `pyproject.toml`
- **Virtual environment**: Located at `.venv` (git-ignored)

Key dependencies:
- `langchain[openai]` – Agent and tool framework
- `langchain-ollama` – Local LLM support (optional)
- `langgraph` – Workflow and state machine orchestration

## Common Commands

### Environment Setup
```bash
# Install dependencies (creates .venv automatically)
uv sync

# Activate virtual environment (if needed)
source .venv/bin/activate
```

### Running the Example
```bash
# Execute the router workflow
python main.py

# The example asks "How do I authenticate API requests?" and shows the routing process.
```

### Dependency Management
```bash
# Add a new package
uv add <package-name>

# Update all dependencies
uv sync --upgrade

# Export locked dependencies
uv lock
```

### Development Tools
```bash
# Run Python interactive shell with dependencies loaded
uv run python

# Run a script with the project environment
uv run python script.py
```

## Architecture

The current code (`main.py`) implements a **router pattern** using LangGraph:

### State Definitions
- `RouterState`: Main workflow state containing query, classifications, results, final answer
- `AgentInput` / `AgentOutput`: Per‑agent input/output schemas
- `Classification`: Routing decision (source, sub‑query)

### Agent Specialization
Three agents are defined, each with its own tools and system prompt:
- **GitHub agent**: Searches code, issues, PRs
- **Notion agent**: Searches documentation pages
- **Slack agent**: Searches team discussions

### Workflow Graph
1. **Classify**: Analyzes the query and generates source‑specific sub‑questions
2. **Route**: Fans out to the relevant agents (conditional edges)
3. **Query each source**: Agents run their tools and return results
4. **Synthesize**: Combines all results into a coherent final answer

The graph is built with `StateGraph` and compiled into a callable workflow.

### Extension Points for AIOps
- **Monitoring tools**: Replace the example tools with system‑monitoring tools (e.g., `psutil` for metrics, `requests` for endpoint health checks)
- **Alert classification**: Extend `classify_query` to recognize anomaly patterns (high CPU, memory leak, disk full)
- **Remediation agents**: Add agents that can execute remediation actions (restart service, clean up disk, adjust config)
- **Multi‑agent collaboration**: Use LangGraph’s `Send` and `Conditional` edges to coordinate multiple monitoring/remediation agents.

## Project Structure

```
.
├── main.py                 # Main router workflow (example)
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 | Locked dependencies (managed by uv)
├── README.md               | High‑level project goals (in Chinese)
├── .python‑version         | Python version (3.12)
└── .gitignore              | Standard Python ignores + .venv
```

## Notes for Future Development

- The example uses mock tools (`search_code`, `search_notion`, etc.). Real tools should be implemented with actual API clients or system calls.
- The router currently supports three fixed sources (`github`, `notion`, `slack`). Adding new sources requires:
  1. Defining a new agent with its own tools and prompt
  2. Extending the `Classification` `Literal` type
  3. Adding a node and edges in the workflow graph
- For production AIOps, consider adding persistent state (checkpoints) and error‑handling nodes to the graph.
- Environment variables (API keys, service endpoints) should be loaded via `os.getenv` or a configuration file; never hard‑code them.