# Tool Use Example (AutoGen + MCP)

This folder demonstrates using an AutoGen `AssistantAgent` with multiple tool sources:

1. A local MCP (Model Context Protocol) math tool server (`math_server.py`) exposing `add` and `multiply`.
2. Locally defined Python functions (`subtract`, `divide`).
3. Optional web search capability (Tavily; Apify SSE adapter scaffolded but disabled by default).

The agent reflects on tool usage and can combine results to answer user tasks.

## What It Does

1. Starts a stdio MCP server (`math_server.py`) and dynamically loads its tools via `mcp_server_tools`.
2. Defines extra arithmetic helpers as simple Python functions (`subtract`, `divide`).
3. Optionally appends a Tavily web search tool if `TAVILY_API_KEY` is set (and could be extended to Apify SSE).
4. Builds a single `AssistantAgent` with `reflect_on_tool_use=True` and a focused system message about minimal web fetches.
5. Streams the responses for two sample tasks (a news‑summary (Iran/US negotiations) and a math question) to the console.

## Quick Start

1. Activate your virtual environment in the project root.
2. Install dependencies (with uv):

   ```bash
   uv sync
   ```

3. Set environment variables (PowerShell example):

   ```powershell
   $Env:OPENAI_API_KEY = "your_key_here"          # or provider-specific key per model config, unless using ollama
   $Env:TAVILY_API_KEY = "your_tavily_key"        # optional (web search)
   # $Env:APIFY_API_KEY = "your_apify_key"       # optional (Apify SSE adapter currently disabled)
   ```

4. Run the example from the sub-project root:

   ```powershell
   uv run main.py
   ```

5. Observe streamed output in the console.

## Customizing

- Toggle `INCLUDE_WEB_SEARCH` to enable/disable external search tools.
- Enable Apify SSE by changing the `if False and os.getenv("APIFY_API_KEY")` guard to `if os.getenv("APIFY_API_KEY")` and ensuring the URL + headers are correct.
- Change the task prompt (currently a geopolitical news summary) to a math expression or a multi-step reasoning question.
- Add additional MCP servers (filesystem, custom APIs) using `StdioServerParams` or `SseServerParams` and extend the `all_tools` list.
- Modify the system message to alter tool invocation strategy (e.g., stricter token budgeting, chain-of-thought hints, etc.).

## Key Components

- `math_server.py` – MCP FastMCP server exposing `add` and `multiply` over stdio.
- `mcp_server_tools(...)` – Discovers and wraps remote (or local) MCP-exposed tools for the agent.
- `subtract`, `divide` – Local Python functions auto-wrapped as tools.
- `SseMcpToolAdapter` / `SseServerParams` – (Scaffold) for integrating SSE-based MCP servers (Apify example commented out).
- `get_tavily_search_tool()` – Provides a web search tool when `TAVILY_API_KEY` is available.
- `AssistantAgent(... reflect_on_tool_use=True ...)` – Enables agent self-reflection on tool outputs to refine answers.

